"""
NEXUS-CI Hybrid RAG Engine
============================
Combines:
  1. Vector similarity (pgvector or in-memory cosine)
  2. Keyword BM25 scoring
  3. Graph context enrichment (Neo4j neighborhood traversal)
  4. Case-scoped authorization filtering

This produces a unified ranked retrieval that leverages all NEXUS-CI data layers.
"""
import math
import re
from typing import Dict, Any, List, Optional
from collections import Counter
from sqlalchemy.orm import Session

from app.models.models import DocumentChunk


class BM25Scorer:
    """
    Okapi BM25 keyword relevance scorer.
    Operates over document chunk text content with case-scoped corpus statistics.
    """
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def score(
        self,
        query_terms: List[str],
        doc_text: str,
        avg_doc_len: float,
        corpus_size: int,
        term_doc_freqs: Dict[str, int]
    ) -> float:
        """Calculate BM25 score for a single document against query terms."""
        doc_terms = doc_text.lower().split()
        doc_len = len(doc_terms)
        if doc_len == 0 or corpus_size == 0:
            return 0.0

        tf_counter = Counter(doc_terms)
        score = 0.0

        for term in query_terms:
            tf = tf_counter.get(term, 0)
            df = term_doc_freqs.get(term, 0)

            # IDF component (with smoothing to avoid log(0))
            idf = math.log((corpus_size - df + 0.5) / (df + 0.5) + 1.0)

            # TF component with length normalization
            tf_norm = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * (doc_len / max(1, avg_doc_len))))

            score += idf * tf_norm

        return score


class HybridRAGEngine:
    """
    Hybrid retrieval engine that fuses vector, keyword, and graph signals.
    """
    def __init__(self, db: Session, neo4j_session=None):
        self.db = db
        self.neo4j = neo4j_session
        self.bm25 = BM25Scorer()

    def retrieve(
        self,
        question: str,
        case_id: Optional[str] = None,
        user_accessible_cases: Optional[List[str]] = None,
        top_k: int = 5,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Hybrid retrieval combining vector + BM25 + graph context.

        Args:
            weights: {"vector": 0.5, "bm25": 0.3, "graph": 0.2} — must sum to 1.0
        """
        w = weights or {"vector": 0.50, "bm25": 0.30, "graph": 0.20}

        # 1. Vector retrieval via existing backend
        from app.services.rag.rag_service import RAGService
        rag = RAGService(self.db)
        vector_result = rag.query_rag(
            question=question,
            case_id=case_id,
            user_accessible_cases=user_accessible_cases,
            top_k=top_k * 3  # Over-retrieve for fusion
        )
        vector_chunks = vector_result.get("retrievedChunks", [])

        # 2. BM25 keyword scoring across same corpus
        query_terms = [t.lower() for t in question.split() if len(t) > 1]

        chunks_query = self.db.query(DocumentChunk)
        if case_id:
            chunks_query = chunks_query.filter(DocumentChunk.case_id == case_id)
        elif user_accessible_cases:
            chunks_query = chunks_query.filter(DocumentChunk.case_id.in_(user_accessible_cases))

        all_chunks = chunks_query.all()
        corpus_size = len(all_chunks)
        avg_doc_len = sum(len((c.text_content or "").split()) for c in all_chunks) / max(1, corpus_size)

        # Pre-compute document frequency for each query term
        term_doc_freqs: Dict[str, int] = {}
        for term in query_terms:
            count = 0
            for c in all_chunks:
                if term in (c.text_content or "").lower():
                    count += 1
            term_doc_freqs[term] = count

        bm25_scores: Dict[str, float] = {}
        for c in all_chunks:
            bm25_score = self.bm25.score(
                query_terms, c.text_content or "", avg_doc_len, corpus_size, term_doc_freqs
            )
            if bm25_score > 0:
                bm25_scores[c.id] = bm25_score

        # 3. Graph context boost — entities mentioned in query that have graph neighbors
        graph_boost: Dict[str, float] = {}
        if self.neo4j:
            try:
                graph_boost = self._get_graph_context_scores(question, case_id)
            except Exception:
                pass  # Graph unavailable, proceed without boost

        # 4. Fusion — build unified score map
        chunk_map: Dict[str, Dict[str, Any]] = {}

        # Add vector results
        max_vec_score = max((c["score"] for c in vector_chunks), default=1.0) or 1.0
        for c in vector_chunks:
            cid = c["chunkId"]
            chunk_map[cid] = {
                **c,
                "vectorScore": c["score"] / max_vec_score,  # Normalize to [0,1]
                "bm25Score": 0.0,
                "graphScore": 0.0,
            }

        # Add BM25 scores
        max_bm25 = max(bm25_scores.values(), default=1.0) or 1.0
        for cid, bm25_val in bm25_scores.items():
            if cid in chunk_map:
                chunk_map[cid]["bm25Score"] = bm25_val / max_bm25
            else:
                # BM25 found a chunk not in vector results — look it up
                c_obj = next((c for c in all_chunks if c.id == cid), None)
                if c_obj:
                    chunk_map[cid] = {
                        "chunkId": c_obj.id,
                        "documentId": c_obj.document_id,
                        "caseId": c_obj.case_id,
                        "sourceType": c_obj.source_type,
                        "chunkIndex": c_obj.chunk_index,
                        "textContent": c_obj.text_content,
                        "score": 0.0,
                        "vectorScore": 0.0,
                        "bm25Score": bm25_val / max_bm25,
                        "graphScore": 0.0,
                    }

        # Add graph boost
        max_graph = max(graph_boost.values(), default=1.0) or 1.0
        for doc_id, g_score in graph_boost.items():
            for cid, entry in chunk_map.items():
                if entry["documentId"] == doc_id:
                    entry["graphScore"] = g_score / max_graph

        # Compute fused score
        for entry in chunk_map.values():
            entry["fusedScore"] = round(
                w["vector"] * entry["vectorScore"]
                + w["bm25"] * entry["bm25Score"]
                + w["graph"] * entry["graphScore"],
                4
            )
            entry["score"] = entry["fusedScore"]

        # Sort by fused score and take top_k
        ranked = sorted(chunk_map.values(), key=lambda x: x["fusedScore"], reverse=True)[:top_k]

        evidence_ids = list(set(item["documentId"] for item in ranked))
        case_ids_out = list(set(item["caseId"] for item in ranked))

        return {
            "question": question,
            "retrievedChunks": ranked,
            "sources": evidence_ids,
            "cases": case_ids_out,
            "matchCount": len(ranked),
            "method": "hybrid",
            "weights": w
        }

    def _get_graph_context_scores(self, question: str, case_id: Optional[str]) -> Dict[str, float]:
        """
        Query Neo4j for entities mentioned in the question,
        then boost documents that those entities are connected to.
        Returns: {document_id: boost_score}
        """
        if not self.neo4j:
            return {}

        # Extract potential entity references from question
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', question)
        phone_patterns = re.findall(r'\b\d{10,}\b', question)
        search_terms = words + phone_patterns

        if not search_terms:
            return {}

        doc_scores: Dict[str, float] = {}

        for term in search_terms:
            try:
                cypher = """
                    MATCH (e)-[r:MENTIONED_IN]->(d)
                    WHERE e.label CONTAINS $term
                    RETURN d.entity_id AS doc_id, count(r) AS mention_count
                """
                result = self.neo4j.run(cypher, term=term)
                for record in result:
                    doc_id = record["doc_id"]
                    count = record["mention_count"]
                    doc_scores[doc_id] = doc_scores.get(doc_id, 0) + count
            except Exception:
                continue

        return doc_scores
