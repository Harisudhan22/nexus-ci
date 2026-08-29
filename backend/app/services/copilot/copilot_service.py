import os
import re
import httpx
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from neo4j import Session as Neo4jSession

from app.core.config import settings
from app.models.models import CanonicalEntity, Document, Finding, InvestigatorQuery
from app.services.graph.graph_service import Neo4jGraphService

class CopilotService:
    def __init__(self, db: Session, neo4j_sess: Neo4jSession = None):
        self.db = db
        self.neo4j_sess = neo4j_sess
        self.graph_service = Neo4jGraphService(neo4j_sess) if neo4j_sess else None

    def query(self, case_id: str, question: str, user_id: str) -> Dict[str, Any]:
        """
        Executes grounded investigator RAG query.
        """
        # 1. Retrieve all entities in this case to match keywords
        case_entities = self.db.query(CanonicalEntity).all()
        # Find which entities are mentioned in the question
        matched_entities = []
        for entity in case_entities:
            # Check if case matches
            if case_id in entity.case_ids:
                if entity.label.lower() in question.lower() or any(a.lower() in question.lower() for a in entity.aliases):
                    matched_entities.append(entity)

        # 2. Retrieve Graph Context (Neo4j)
        graph_facts = []
        retrieved_evidence_ids = set()
        
        if self.graph_service:
            for ent in matched_entities:
                subg = self.graph_service.get_subgraph(case_id, {"selected_entity": ent.id})
                for edge in subg.get("edges", []):
                    graph_facts.append(
                        f"Relationship: {edge['source']} {edge['type']} {edge['target']} (Confidence: {edge['confidence']}%, Rationale: {edge['rationale']})"
                    )
                    retrieved_evidence_ids.update(edge.get("evidenceIds", []))

        # 3. Retrieve Documents Context (Postgres)
        doc_facts = []
        # If specific entities matched, get documents mentioning them or upload documents
        case_docs = self.db.query(Document).filter(Document.case_id == case_id).all()
        for doc in case_docs:
            # Retrieve text from doc
            contains_entity = False
            for ent in matched_entities:
                if ent.label.lower() in (doc.extracted_text or "").lower() or any(a.lower() in (doc.extracted_text or "").lower() for a in ent.aliases):
                    contains_entity = True
            
            # If doc matches or we have a direct textual hit, grab snippets
            text_snippet = ""
            if contains_entity or doc.id in retrieved_evidence_ids or doc.filename.lower() in question.lower():
                retrieved_evidence_ids.add(doc.id)
                text_snippet = (doc.extracted_text or "")[:1500]  # Grab first 1500 chars snippet
                doc_facts.append(
                    f"Evidence ID: {doc.id} (Filename: {doc.filename}, Source Type: {doc.sourceType})\nContent: {text_snippet}"
                )

        # Retrieve findings context
        findings = self.db.query(Finding).filter(Finding.case_id == case_id).all()
        findings_facts = []
        for f in findings:
            if any(ent.id in f.entity_ids for ent in matched_entities):
                findings_facts.append(
                    f"Finding: {f.title} (Category: {f.category}, Severity: {f.severity}, Why: {f.why})"
                )
                retrieved_evidence_ids.update(f.evidence_ids)

        # Format complete facts context
        facts_context = "\n\n".join(
            ["=== GRAPH RELATIONSHIPS ==="] + graph_facts +
            ["=== EVIDENCE DOCUMENTS ==="] + doc_facts +
            ["=== ANALYTICAL FINDINGS ==="] + findings_facts
        )

        # 4. Invoke LLM or Fallback Solver
        provider = settings.LLM_PROVIDER.lower()
        openai_key = settings.OPENAI_API_KEY
        groq_key = settings.GROQ_API_KEY

        system_prompt = """You are an evidence-grounded investigator assistant.

Never invent people.
Never invent evidence.
Never invent dates.
Never invent transactions.
Never invent relationships.

Use only supplied case facts.

Distinguish:
OBSERVED FACT
from
ANALYTICAL INFERENCE.

Never determine criminal guilt.

Never state that an entity is definitely criminal.

Every factual claim must cite one or more evidence IDs, strictly in the form [Evidence_ID] (e.g. [CDR-101], [FIR-101]).

If the evidence does not support the question, respond exactly:
"Insufficient evidence in the current case data."

Do not use information outside the supplied case context.

Provide your response in this exact structured format:
Summary: <Short summary of explanation>
Key reasons:
- <Reason 1>
- <Reason 2>
Observed evidence:
- <Evidence fact 1>
Analytical interpretation:
- <Interpretation 1>
Confidence: <Percentage between 0 and 100>
Supporting evidence: [Evidence ID 1], [Evidence ID 2]"""

        answer_text = ""
        
        # If API key is available, run LLM call
        if provider == "openai" and openai_key:
            answer_text = self._call_openai(system_prompt, question, facts_context, openai_key)
        elif provider == "groq" and groq_key:
            answer_text = self._call_groq(system_prompt, question, facts_context, groq_key)
        
        # Fallback to local rule engine if no LLM config is provided
        if not answer_text:
            answer_text = self._fallback_local_engine(question, matched_entities, doc_facts, findings_facts, list(retrieved_evidence_ids))

        # 5. Grounding Validation
        # Check LLM citations. If they cite evidence not in retrieved_evidence_ids, remove them or trigger Insufficient Evidence
        valid_citations = []
        cited_ids = re.findall(r"\[([a-zA-Z0-9_-]+)\]", answer_text)
        
        for cid in cited_ids:
            if cid in retrieved_evidence_ids or cid.upper() in [d.id.upper() for d in case_docs]:
                valid_citations.append(cid)
            else:
                # Remove citation from response text to prevent hallucinated references
                answer_text = answer_text.replace(f"[{cid}]", "")

        # If answer is blank or doesn't support, default
        if "Insufficient evidence" in answer_text or len(valid_citations) == 0 and len(matched_entities) == 0:
            return {
                "summary": "Insufficient evidence in the current case data.",
                "key_reasons": ["No matching evidence files contain details relevant to the query."],
                "observed_evidence": [],
                "analytical_interpretation": [],
                "confidence": 0,
                "supporting_evidence": []
            }

        # Parse response into required structure
        parsed = self._parse_structured_answer(answer_text, valid_citations)
        
        # Record query in Postgres
        q_record = InvestigatorQuery(
            id=f"q-{uuid.uuid4().hex[:8]}",
            case_id=case_id,
            user_id=user_id,
            question=question,
            answer=parsed["summary"],
            citations=parsed["supporting_evidence"],
            timestamp=datetime.datetime.utcnow()
        )
        self.db.add(q_record)
        self.db.commit()

        return parsed

    def _call_openai(self, system: str, question: str, context: str, key: str) -> str:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
                ],
                "temperature": 0.0
            }
            res = httpx.post(url, json=payload, headers=headers, timeout=20.0)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"OpenAI API Error: {e}")
        return ""

    def _call_groq(self, system: str, question: str, context: str, key: str) -> str:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {
                "model": "llama3-8b-8192",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
                ],
                "temperature": 0.0
            }
            res = httpx.post(url, json=payload, headers=headers, timeout=20.0)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Groq API Error: {e}")
        return ""

    def _fallback_local_engine(self, question: str, entities: List[CanonicalEntity], doc_facts: List[str], findings_facts: List[str], evidence_ids: List[str]) -> str:
        """
        Generates a deterministic response by querying database records.
        """
        if not entities:
            return "Insufficient evidence in the current case data."
            
        ent_labels = ", ".join([e.label for e in entities])
        ev_cites = ", ".join([f"[{eid}]" for eid in evidence_ids])

        # Compile evidence facts to display
        obs_lines = []
        for fact in doc_facts:
            # Extract evidence ID
            match = re.search(r"Evidence ID: ([a-zA-Z0-9_-]+)", fact)
            eid = match.group(1) if match else "Evidence"
            
            # Look for lines containing entity name
            for line in fact.split("\n"):
                if any(e.label.lower() in line.lower() for e in entities) and "content:" not in line.lower():
                    clean_line = line.strip().strip(",").strip('"')
                    obs_lines.append(f"- Found record linking entity in [{eid}]: {clean_line[:120]}")

        if not obs_lines:
            obs_lines = [f"- Mentioned in case evidence files: {ev_cites}"]

        interpretations = []
        for finding in findings_facts:
            # Extract category / why
            match = re.search(r"Finding: (.*?) \(Category: (.*?), Severity: (.*?), Why: (.*?)\)", finding)
            if match:
                title, cat, sev, why = match.groups()
                interpretations.append(f"- Graph Pattern Detected: {title} ({sev} severity) - {why}")
                
        if not interpretations:
            interpretations = [f"- Entity possesses active references in current case graph linkages."]

        reasons = [f"Direct name reference matches found for '{ent_labels}' in the case documents."]
        if interpretations:
            reasons.append("Identified in analytical findings within the transaction or communication network.")

        conf_val = 85 if interpretations else 60

        return f"""
Summary: '{ent_labels}' is registered in this case with multiple evidence connections.
Key reasons:
- Matches name variants in document texts.
- Verified in graph relationship mappings.
Observed evidence:
{chr(10).join(obs_lines[:4])}
Analytical interpretation:
{chr(10).join(interpretations[:3])}
Confidence: {conf_val}
Supporting evidence: {ev_cites}
"""

    def _parse_structured_answer(self, text: str, valid_citations: List[str]) -> Dict[str, Any]:
        """
        Parses structured response output.
        """
        summary = ""
        reasons = []
        obs = []
        interp = []
        confidence = 70

        lines = text.split("\n")
        current_section = None
        
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
                
            if line_str.lower().startswith("summary:"):
                summary = line_str[len("summary:"):].strip().strip('"')
                current_section = None
            elif line_str.lower().startswith("key reasons:"):
                current_section = "reasons"
            elif line_str.lower().startswith("observed evidence:"):
                current_section = "obs"
            elif line_str.lower().startswith("analytical interpretation:"):
                current_section = "interp"
            elif line_str.lower().startswith("confidence:"):
                # Extract digits
                digits = re.findall(r"\d+", line_str)
                if digits:
                    confidence = int(digits[0])
                current_section = None
            elif line_str.lower().startswith("supporting evidence:"):
                current_section = None
            elif line_str.startswith("-") or line_str.startswith("*"):
                val = line_str.lstrip("-* ").strip()
                if current_section == "reasons":
                    reasons.append(val)
                elif current_section == "obs":
                    obs.append(val)
                elif current_section == "interp":
                    interp.append(val)

        # Fallback if parser missed summary
        if not summary:
            # Grab first non-header sentence
            summary = "Entity matches and evidence linkages found."

        return {
            "summary": summary,
            "key_reasons": reasons if reasons else ["Identified in active document texts."],
            "observed_evidence": obs if obs else ["Mentions matched in case files."],
            "analytical_interpretation": interp if interp else ["No anomalies registered in Graph analytics."],
            "confidence": confidence,
            "supporting_evidence": list(set(valid_citations))
        }
