import os
import re
import json
import uuid
import datetime
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.orm import Session

from app.models.models import (
    CanonicalEntity, Document, EntityRelationship, Finding,
    InvestigatorQuery, Case, AuditLog, User
)
from app.services.graph.graph_service import Neo4jGraphService
from app.services.rag.rag_service import RAGService
from app.services.analytics.graph_analytics import GraphAnalyticsService
from app.core.dependencies import get_accessible_case_ids

class CopilotService:
    def __init__(self, db: Session, graph_service: Optional[Neo4jGraphService] = None):
        self.db = db
        self.graph_service = graph_service or Neo4jGraphService(session=None, db=db)
        self.rag_service = RAGService(db)
        self.analytics_service = GraphAnalyticsService(db)

    def query(self, case_id: str, question: str, user_id: str) -> Dict[str, Any]:
        """Unified multi-source grounded solver combining Graph + RAG + Relational DB."""
        q_lower = question.lower()
        user = self.db.query(User).filter(User.id == user_id).first()
        accessible_cases = get_accessible_case_ids(user, self.db) if user else [case_id]

        # 1. Entity Recognition & Scope Check
        all_entities = self.db.query(CanonicalEntity).all()
        matched_entities = []
        for ent in all_entities:
            entity_case_ids = [cid for cid in ent.case_ids if accessible_cases is None or cid in accessible_cases]
            if case_id not in entity_case_ids:
                continue
            # Matches label or aliases
            if ent.label.lower() in q_lower or any(str(a).lower() in q_lower for a in ent.aliases):
                matched_entities.append(ent)

        # 2. RAG Document Retrieval
        rag_results = self.rag_service.query_rag(question=question, case_id=case_id, top_k=5)
        retrieved_chunks = rag_results.get("retrievedChunks", [])
        evidence_ids = rag_results.get("sources", [])

        # 3. Graph Analytics & Graph Context
        graph_facts = []
        centrality = self.analytics_service.compute_centrality(case_id=case_id)
        
        if matched_entities:
            for ent in matched_entities:
                subg = self.graph_service.get_subgraph(case_id, {"selected_entity": ent.id})
                for edge in subg.get("edges", []):
                    graph_facts.append(f"Relationship: {edge['source']} {edge['type']} {edge['target']} (Confidence: {edge['confidence']}%)")
                    if edge.get("evidenceIds"):
                        evidence_ids.extend(edge["evidenceIds"])

        # 4. Handle Specific Intent Patterns Deterministically
        answer_text = ""
        confidence = 85
        limitations = []

        # Intent: Cross-case connections for an entity
        if "previous cases" in q_lower or "connected to" in q_lower or "cross-case" in q_lower:
            if matched_entities:
                target = matched_entities[0]
                cases_list = [cid for cid in target.case_ids if accessible_cases is None or cid in accessible_cases]
                answer_text = f"Entity '{target.label}' ({target.type}) is connected to {len(cases_list)} cases: {', '.join(cases_list)}. Key identifiers: {json.dumps(target.attributes)}."
            else:
                answer_text = f"Cross-case network query for case {case_id}: {question}"

        # Intent: Strongest bridge / centrality
        elif "bridge" in q_lower or "central" in q_lower or "most connected" in q_lower:
            top_bridges = centrality.get("topBridges", [])
            if top_bridges:
                b_names = [f"{b['label']} (Betweenness: {b['betweennessCentrality']})" for b in top_bridges[:3]]
                answer_text = f"The primary structural bridge entities in this network are: {', '.join(b_names)}. These nodes link distinct clusters."
            else:
                answer_text = f"Network centrality query for case {case_id}: {question}"

        # Intent: Case summary
        elif "summarize" in q_lower or "summary" in q_lower or "overview" in q_lower:
            c_obj = self.db.query(Case).filter(Case.id == case_id).first()
            if c_obj:
                answer_text = f"Case {c_obj.id} ({c_obj.title}): {c_obj.description}. Assigned Agency: {c_obj.agency}, Police Station: {c_obj.police_station or 'Central PS'}."
            else:
                answer_text = ""

        # Intent: Generic RAG-driven synthesis
        else:
            # Check if query specifically names a canonical entity
            target_ent = None
            for ent in matched_entities:
                lbl = ent.label.lower()
                if lbl in q_lower or any(a.lower() in q_lower for a in (ent.aliases or [])):
                    target_ent = ent
                    break

            if target_ent:
                # Find chunks matching target entity
                ent_chunks = [c for c in retrieved_chunks if target_ent.label.lower() in c.get("textContent", "").lower()]
                best_chunk = ent_chunks[0] if ent_chunks else (retrieved_chunks[0] if retrieved_chunks else None)
                
                parts = [f"Canonical Entity: '{target_ent.label}' ({target_ent.type.upper()})."]
                if target_ent.subtitle:
                    parts.append(f"Role: {target_ent.subtitle}.")
                if target_ent.attributes:
                    parts.append(f"Attributes: {json.dumps(target_ent.attributes)}.")
                if best_chunk:
                    clean = re.sub(r"(?i)(ignore\s+(all\s+)?previous|system\s+prompt)", "[REDACTED]", best_chunk["textContent"])
                    parts.append(f"Evidence Citation ({best_chunk['documentId']}): \"{clean[:220]}...\"")
                answer_text = " ".join(parts)
            elif retrieved_chunks:
                raw_text = retrieved_chunks[0]["textContent"]
                clean_text = re.sub(
                    r"(?i)(ignore\s+(all\s+)?previous(\s+system)?\s+instructions?|system\s+prompt|say\s+this\s+person|say\s+person\s+\w+\s+is\s+guilty|say\s+[\w\s]+\s+is\s+guilty)",
                    "[REDACTED_DIRECTIVE]",
                    raw_text
                )
                answer_text = f"Based on evidence chunk from {retrieved_chunks[0]['documentId']}: \"{clean_text[:300]}...\""
            elif matched_entities:
                target = matched_entities[0]
                answer_text = f"Entity '{target.label}' ({target.type}) is registered in case {case_id}. Role/Subtitle: {target.subtitle or 'Associate'}. Attributes: {json.dumps(target.attributes)}."

        # Grounding Enforcement: Check if no retrieved facts
        if not answer_text or (not retrieved_chunks and not matched_entities and not graph_facts):
            return {
                "answer": "Insufficient evidence in the current dataset.",
                "summary": "Insufficient evidence in the current dataset.",
                "confidence": 0,
                "provider_type": "LOCAL_FALLBACK",
                "providerType": "LOCAL_FALLBACK",
                "provider_name": "grounded_local",
                "providerName": "grounded_local",
                "model": "GroundedLocalSolver",
                "is_real_llm": False,
                "sources": [],
                "cases": [case_id] if case_id else [],
                "entities": [],
                "evidence": [],
                "observed_evidence": [],
                "supporting_evidence": [],
                "key_reasons": ["No matching evidence documents or canonical graph edges support this query."],
                "analytical_interpretation": ["Grounding rule enforced: zero-hallucination policy."],
                "graphFacts": [],
                "limitations": ["No matching evidence documents or canonical graph edges support this query."]
            }

        unique_evidence = list(set(evidence_ids))
        unique_cases = list(set(
            [case_id] + [
                c for e in matched_entities for c in e.case_ids
                if accessible_cases is None or c in accessible_cases
            ]
        ))
        unique_entity_ids = list(set([e.id for e in matched_entities]))
        evidence_context = {
            "caseId": case_id,
            "matchedEntities": [
                {
                    "id": ent.id,
                    "type": ent.type,
                    "label": ent.label,
                    "aliases": ent.aliases,
                    "case_ids": [cid for cid in ent.case_ids if accessible_cases is None or cid in accessible_cases],
                    "attributes": ent.attributes,
                }
                for ent in matched_entities
            ],
            "chunks": [
                {
                    **chunk,
                    "textContent": re.sub(
                        r"(?i)(ignore\s+(all\s+)?previous(\s+system)?\s+instructions?|system\s+prompt|say\s+this\s+person|say\s+person\s+\w+\s+is\s+guilty|say\s+[\w\s]+\s+is\s+guilty)",
                        "[REDACTED_DIRECTIVE]",
                        chunk.get("textContent", ""),
                    )
                }
                for chunk in retrieved_chunks
            ],
            "graphFacts": graph_facts[:5],
            "draftAnswer": answer_text,
        }

        from app.services.copilot.llm_provider import get_llm_provider, GroqProvider
        llm = get_llm_provider()
        llm_response = llm.generate_answer(question, evidence_context)

        # Multi-Provider Outage Fallback: If Gemini fails, fallback to Groq REAL_LLM if available
        if llm_response.get("error") and getattr(llm, "provider_name", "") == "gemini":
            groq_key = os.getenv("GROQ_API_KEY", "").strip()
            if groq_key:
                try:
                    groq_model = os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b").strip() or "qwen/qwen3.6-27b"
                    fallback_llm = GroqProvider(api_key=groq_key, model=groq_model)
                    fallback_res = fallback_llm.generate_answer(question, evidence_context)
                    if not fallback_res.get("error"):
                        llm = fallback_llm
                        llm_response = fallback_res
                except Exception:
                    pass

        provider_summary = llm_response.get("summary") or ""
        provider_type = llm_response.get("providerType", getattr(llm, "provider_type", "LOCAL_FALLBACK"))
        if provider_type == "REAL_LLM" and provider_summary:
            answer_text = provider_summary

        provider_name = llm_response.get("providerName") or llm_response.get("provider_name") or getattr(llm, "provider_name", "grounded_local")
        model_name = llm_response.get("model") or getattr(llm, "model", "GroundedLocalSolver")
        is_real_llm = llm_response.get("is_real_llm", getattr(llm, "is_real_llm", False))

        result = {
            "answer": answer_text,
            "summary": answer_text,
            "confidence": confidence,
            "provider_type": provider_type,
            "providerType": provider_type,
            "provider_name": provider_name,
            "providerName": provider_name,
            "model": model_name,
            "is_real_llm": is_real_llm,
            "sources": unique_evidence,
            "cases": unique_cases,
            "entities": unique_entity_ids,
            "evidence": unique_evidence,
            "observed_evidence": unique_evidence,
            "supporting_evidence": unique_evidence,
            "key_reasons": ["Matched canonical entity & RAG document chunk evidence."],
            "analytical_interpretation": [f"Grounded analysis for case {case_id} across multi-source evidence."],
            "graph_facts": graph_facts[:5],
            "graphFacts": graph_facts[:5],
            "limitations": limitations if limitations else ["Analysis constrained to ingested historical evidence records."]
        }

        # 5. Persist Query in Postgres
        try:
            q_obj = InvestigatorQuery(
                id=f"qry-{uuid.uuid4().hex[:8]}",
                case_id=case_id,
                user_id=user_id,
                question=question,
                answer=answer_text,
                citations=unique_evidence,
                timestamp=datetime.datetime.utcnow()
            )
            self.db.add(q_obj)
            self.db.commit()
        except Exception:
            self.db.rollback()

        return result
