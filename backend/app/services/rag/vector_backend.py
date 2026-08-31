"""
NEXUS-CI Vector Backend Abstraction
===================================
Provides native pgvector PostgreSQL similarity search with automatic in-memory fallback.
Supports embedding dimension tracking, startup validation, reindexing, and diagnostics.
"""
import os
import time
import json
import math
import hashlib
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.models import DocumentChunk, Document


# Dimensionality constants
DETERMINISTIC_EMBEDDING_DIM = 64
TRANSFORMER_EMBEDDING_DIM = 384


def get_current_embedding_dim() -> int:
    """Returns the active embedding dimension based on configuration."""
    if os.getenv("USE_TRANSFORMERS", "").lower() == "true":
        return TRANSFORMER_EMBEDDING_DIM
    return DETERMINISTIC_EMBEDDING_DIM


def get_current_embedding_model_name() -> str:
    """Returns the active embedding model name."""
    if os.getenv("USE_TRANSFORMERS", "").lower() == "true":
        return "all-MiniLM-L6-v2 (SentenceTransformer)"
    return "deterministic_feature_hash_64"


class VectorBackendConfigurationError(RuntimeError):
    """Raised when native pgvector is required (VECTOR_FALLBACK_ENABLED=false) but is not installed or available."""
    pass


def is_fallback_enabled() -> bool:
    """Returns True if fallback to in-memory vector backend is enabled."""
    raw = os.getenv("VECTOR_FALLBACK_ENABLED", "false").strip().lower()
    return raw in ("true", "1", "yes")


class BaseVectorBackend:
    backend_name: str = "base"
    is_native_pgvector: bool = False

    def search_chunks(
        self,
        db: Session,
        query_vector: List[float],
        case_id: Optional[str] = None,
        user_accessible_cases: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError


class NativePgVectorBackend(BaseVectorBackend):
    """
    Native PostgreSQL pgvector extension backend.
    Uses native SQL vector operations (cosine distance: <=>) against vector columns.
    """
    backend_name: str = "pgvector"
    is_native_pgvector: bool = True

    def search_chunks(
        self,
        db: Session,
        query_vector: List[float],
        case_id: Optional[str] = None,
        user_accessible_cases: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        # Check if database is SQLite (unit test environment) or if pgvector extension is missing
        is_sqlite = False
        try:
            if db and hasattr(db, "bind") and db.bind and db.bind.dialect.name == "sqlite":
                is_sqlite = True
        except Exception:
            pass

        if is_sqlite or not check_pgvector_available(db):
            if not is_fallback_enabled() and not is_sqlite:
                raise VectorBackendConfigurationError(
                    "PGVECTOR_REQUIRED_BUT_UNAVAILABLE: Native pgvector extension is required "
                    "(VECTOR_FALLBACK_ENABLED=false) but is not installed or active in the PostgreSQL database."
                )
            # Fallback enabled or SQLite unit test DB: use in-memory backend
            return InMemoryVectorBackend().search_chunks(db, query_vector, case_id, user_accessible_cases, top_k)

        # Format query vector as PostgreSQL vector string [0.1, 0.2, ...]
        vec_str = "[" + ",".join(str(round(v, 6)) for v in query_vector) + "]"
        
        where_clauses = ["embedding IS NOT NULL"]
        params: Dict[str, Any] = {"vec": vec_str, "limit": top_k}

        if case_id:
            where_clauses.append("case_id = :case_id")
            params["case_id"] = case_id
        elif user_accessible_cases:
            where_clauses.append("case_id = ANY(:user_cases)")
            params["user_cases"] = user_accessible_cases

        where_sql = f"WHERE {' AND '.join(where_clauses)}"

        # Try native pgvector distance operator <=> against the embedding column
        try:
            sql = f"""
                SELECT id, document_id, case_id, source_type, chunk_index, text_content,
                       1 - (embedding <=> CAST(:vec AS vector)) AS score
                FROM document_chunks
                {where_sql}
                ORDER BY embedding <=> CAST(:vec AS vector)
                LIMIT :limit
            """
            result = db.execute(text(sql), params).fetchall()
            if result:
                return [
                    {
                        "chunkId": r[0],
                        "documentId": r[1],
                        "caseId": r[2],
                        "sourceType": r[3],
                        "chunkIndex": r[4],
                        "textContent": r[5],
                        "score": round(float(r[6]), 4) if r[6] is not None else 0.0
                    }
                    for r in result
                ]
        except Exception as e:
            db.rollback()
            if not is_fallback_enabled():
                raise VectorBackendConfigurationError(
                    f"PGVECTOR_REQUIRED_BUT_UNAVAILABLE: Native pgvector query failed ({str(e)}) "
                    "and fallback is disabled (VECTOR_FALLBACK_ENABLED=false)."
                )

        # Fall back to in-memory vector calculations if query yields no rows or fallback is enabled
        if is_fallback_enabled():
            return InMemoryVectorBackend().search_chunks(db, query_vector, case_id, user_accessible_cases, top_k)
        return []


class InMemoryVectorBackend(BaseVectorBackend):
    """
    Python in-memory Cosine Similarity & Keyword Boost vector backend.
    Used for local development, unit tests, and SQLite/PostgreSQL standard instances.
    """
    backend_name: str = "in_memory"
    is_native_pgvector: bool = False

    def search_chunks(
        self,
        db: Session,
        query_vector: List[float],
        case_id: Optional[str] = None,
        user_accessible_cases: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        chunks_query = db.query(DocumentChunk)
        if case_id:
            chunks_query = chunks_query.filter(DocumentChunk.case_id == case_id)
        elif user_accessible_cases:
            chunks_query = chunks_query.filter(DocumentChunk.case_id.in_(user_accessible_cases))

        all_chunks = chunks_query.all()
        scored = []
        for c in all_chunks:
            c_vec = c.embedding_json or []
            if not c_vec:
                continue
            
            # Cosine similarity
            if len(query_vector) == len(c_vec) and any(query_vector) and any(c_vec):
                dot = sum(a * b for a, b in zip(query_vector, c_vec))
                score = max(0.0, float(dot))
            else:
                score = 0.0

            if score >= 0.10:
                scored.append({
                    "chunkId": c.id,
                    "documentId": c.document_id,
                    "caseId": c.case_id,
                    "sourceType": c.source_type,
                    "chunkIndex": c.chunk_index,
                    "textContent": c.text_content,
                    "score": round(score, 4)
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


def get_vector_backend(override_backend: Optional[str] = None) -> BaseVectorBackend:
    """Factory returning configured vector backend."""
    target = (override_backend or os.getenv("VECTOR_BACKEND") or "pgvector").strip().lower()
    if target == "pgvector":
        return NativePgVectorBackend()
    return InMemoryVectorBackend()


def check_pgvector_available(db: Session) -> bool:
    """Checks if native pgvector extension is active in PostgreSQL."""
    try:
        res = db.execute(text("SELECT extname FROM pg_extension WHERE extname='vector'")).fetchall()
        return len(res) > 0
    except Exception:
        return False


def get_vector_status(db: Session) -> Dict[str, Any]:
    """Returns comprehensive startup / diagnostic status for the vector backend."""
    target_backend = (os.getenv("VECTOR_BACKEND") or "pgvector").strip().lower()
    fallback_enabled = is_fallback_enabled()
    native_available = check_pgvector_available(db)
    
    total_chunks = 0
    indexed_chunks = 0
    try:
        total_chunks = db.query(DocumentChunk).count()
        indexed_chunks = db.query(DocumentChunk).filter(DocumentChunk.embedding_json.isnot(None)).count()
    except Exception:
        pass

    if target_backend == "pgvector":
        if native_available:
            active_backend = "pgvector"
            fallback_active = False
            fallback_reason = None
            status_code = "HEALTHY"
        elif fallback_enabled:
            active_backend = "in_memory"
            fallback_active = True
            fallback_reason = "PostgreSQL vector extension unavailable"
            status_code = "DEGRADED_FALLBACK"
        else:
            active_backend = "none"
            fallback_active = False
            fallback_reason = "PostgreSQL vector extension unavailable and fallback disabled"
            status_code = "PGVECTOR_REQUIRED_BUT_UNAVAILABLE"
    else:
        active_backend = "in_memory"
        fallback_active = False
        fallback_reason = None
        status_code = "HEALTHY"

    res = {
        "configured_backend": target_backend,
        "active_backend": active_backend,
        "vector_backend": active_backend,
        "native_pgvector_available": native_available,
        "pgvector_available": native_available,
        "is_native_pgvector": (active_backend == "pgvector"),
        "fallback_enabled": fallback_enabled,
        "fallback_active": fallback_active,
        "embedding_dimension": get_current_embedding_dim(),
        "embedding_model": get_current_embedding_model_name(),
        "total_chunks": total_chunks,
        "indexed_chunks": indexed_chunks,
        "indexing_status": "synced" if total_chunks == indexed_chunks else "pending_reindex",
        "status_code": status_code
    }

    if fallback_reason:
        res["fallback_reason"] = fallback_reason
    if status_code == "PGVECTOR_REQUIRED_BUT_UNAVAILABLE":
        res["error"] = "Native pgvector required (VECTOR_FALLBACK_ENABLED=false) but unavailable in database"

    return res


def reindex_all_chunks(db: Session, case_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Re-indexes document chunks and regenerates embeddings with active dimension.
    Idempotent, auditable, does not duplicate chunks.
    """
    start_time = time.time()
    from app.services.rag.rag_service import RAGService
    rag_svc = RAGService(db)

    chunks_query = db.query(DocumentChunk)
    if case_id:
        chunks_query = chunks_query.filter(DocumentChunk.case_id == case_id)

    chunks = chunks_query.all()
    if not chunks:
        # If no chunks exist yet, chunk existing documents
        docs_query = db.query(Document)
        if case_id:
            docs_query = docs_query.filter(Document.case_id == case_id)
        for doc in docs_query.all():
            if doc.extracted_text:
                rag_svc.chunk_document(doc.id, doc.case_id, doc.extracted_text, source_type=doc.source_type)
        chunks = chunks_query.all()

    total = len(chunks)
    processed = 0
    success = 0
    failed = 0

    for chunk in chunks:
        processed += 1
        try:
            new_emb = rag_svc.generate_embedding(chunk.text_content)
            chunk.embedding_json = new_emb
            
            # If native pgvector column is present, attempt to update it
            try:
                vec_str = "[" + ",".join(str(round(v, 6)) for v in new_emb) + "]"
                db.execute(
                    text("UPDATE document_chunks SET embedding = CAST(:vec AS vector) WHERE id = :cid"),
                    {"vec": vec_str, "cid": chunk.id}
                )
            except Exception:
                pass
            
            success += 1
        except Exception:
            failed += 1

    db.commit()
    duration_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "total": total,
        "processed": processed,
        "success": success,
        "failed": failed,
        "duration_ms": duration_ms,
        "case_id": case_id,
        "dimension": get_current_embedding_dim()
    }
