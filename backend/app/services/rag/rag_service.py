import os
import math
import json
import hashlib
import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.models import Document, DocumentChunk

class SimpleVectorSearch:
    """Lightweight deterministic vector embedding & cosine similarity solver."""
    @staticmethod
    def text_to_vector(text: str) -> List[float]:
        # Hash text features into 64-dimensional float embedding vector
        words = text.lower().split()
        dim = 64
        vec = [0.0] * dim
        for w in words:
            idx = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16) % dim
            vec[idx] += 1.0
        
        # Normalize to unit length
        magnitude = math.sqrt(sum(v * v for v in vec))
        if magnitude > 0:
            vec = [v / magnitude for v in vec]
        return vec

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        return float(dot)

class RAGService:
    def __init__(self, db: Session):
        self.db = db
        # Attempt to use sentence-transformers if available
        self.model = None
        if os.getenv("USE_TRANSFORMERS", "").lower() == "true":
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                self.model = None

    def generate_embedding(self, text: str) -> List[float]:
        """Generates embedding vector using SentenceTransformers or fallback vectorizer."""
        if self.model:
            try:
                emb = self.model.encode(text)
                return emb.tolist()
            except Exception:
                pass
        return SimpleVectorSearch.text_to_vector(text)

    def chunk_document(
        self,
        document_id: str,
        case_id: str,
        text_content: str,
        source_type: str = "FIR",
        chunk_size: int = 400,
        overlap: int = 80
    ) -> List[DocumentChunk]:
        """Splits document text into overlapping chunks, embeds them, and stores provenance in PostgreSQL."""
        if not text_content or not text_content.strip():
            return []

        # Remove existing chunks for this document to ensure idempotency
        self.db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        self.db.commit()

        clean_text = text_content.strip()
        words = clean_text.split()
        
        chunks_text = []
        if len(words) <= chunk_size:
            chunks_text.append(clean_text)
        else:
            step = chunk_size - overlap
            for i in range(0, len(words), step):
                chunk_words = words[i:i + chunk_size]
                if chunk_words:
                    chunks_text.append(" ".join(chunk_words))

        created_chunks = []
        for idx, c_text in enumerate(chunks_text):
            c_sha256 = hashlib.sha256(c_text.encode("utf-8")).hexdigest()
            c_emb = self.generate_embedding(c_text)

            chunk_obj = DocumentChunk(
                id=f"chk-{document_id}-{idx + 1}",
                document_id=document_id,
                case_id=case_id,
                source_type=source_type,
                page=1,
                chunk_index=idx + 1,
                text_content=c_text,
                embedding_json=c_emb,
                sha256=c_sha256
            )
            self.db.add(chunk_obj)
            created_chunks.append(chunk_obj)

        # Mark Document processing_status as completed
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.processing_status = "completed"

        self.db.commit()
        return created_chunks

    def query_rag(
        self,
        question: str,
        case_id: Optional[str] = None,
        user_accessible_cases: Optional[List[str]] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """Executes vector similarity retrieval for a question across case-scoped document chunks."""
        q_emb = self.generate_embedding(question)

        chunks_query = self.db.query(DocumentChunk)
        if case_id:
            chunks_query = chunks_query.filter(DocumentChunk.case_id == case_id)
        elif user_accessible_cases:
            chunks_query = chunks_query.filter(DocumentChunk.case_id.in_(user_accessible_cases))

        all_chunks = chunks_query.all()
        if not all_chunks:
            # Fallback: if no chunks pre-indexed, auto-index existing documents for this case
            docs_query = self.db.query(Document)
            if case_id:
                docs_query = docs_query.filter(Document.case_id == case_id)
            elif user_accessible_cases:
                docs_query = docs_query.filter(Document.case_id.in_(user_accessible_cases))

            for d in docs_query.all():
                if d.extracted_text:
                    self.chunk_document(d.id, d.case_id, d.extracted_text, source_type=d.source_type)

            all_chunks = chunks_query.all()

        scored_chunks = []
        for c in all_chunks:
            c_emb = c.embedding_json or SimpleVectorSearch.text_to_vector(c.text_content)
            score = SimpleVectorSearch.cosine_similarity(q_emb, c_emb)
            
            # Keyword bonus if exact phrase match
            q_words = set(question.lower().split())
            c_words = set(c.text_content.lower().split())
            overlap_ratio = len(q_words.intersection(c_words)) / max(1, len(q_words))
            combined_score = round(float(score * 0.7 + overlap_ratio * 0.3), 4)

            if combined_score > 0.05:
                scored_chunks.append({
                    "chunkId": c.id,
                    "documentId": c.document_id,
                    "caseId": c.case_id,
                    "sourceType": c.source_type,
                    "chunkIndex": c.chunk_index,
                    "textContent": c.text_content,
                    "score": combined_score
                })

        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        top_chunks = scored_chunks[:top_k]

        evidence_ids = list(set(item["documentId"] for item in top_chunks))
        case_ids = list(set(item["caseId"] for item in top_chunks))

        return {
            "question": question,
            "retrievedChunks": top_chunks,
            "sources": evidence_ids,
            "cases": case_ids,
            "matchCount": len(top_chunks)
        }
