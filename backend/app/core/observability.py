"""
NEXUS-CI Observability & Health Diagnostics
=============================================
Provides:
  1. Structured JSON logging for production traceability
  2. Deep health check endpoint (DB, Neo4j, queue, storage)
  3. System metrics collection
"""
import os
import json
import time
import logging
import datetime
import platform
from typing import Dict, Any, Optional


# ── Structured Logger ────────────────────────────────────────────

class StructuredFormatter(logging.Formatter):
    """JSON-line structured log formatter for production observability."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "case_id"):
            log_entry["case_id"] = record.case_id
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])

        return json.dumps(log_entry)


def get_logger(name: str = "nexus-ci") -> logging.Logger:
    """Get a structured logger for the application."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        use_json = os.getenv("LOG_FORMAT", "text").lower() == "json"
        if use_json:
            handler.setFormatter(StructuredFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
            ))
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))

    return logger


# ── Deep Health Check ────────────────────────────────────────────

def check_health_deep() -> Dict[str, Any]:
    """
    Comprehensive health check across all NEXUS-CI subsystems.
    Returns subsystem-level status for monitoring dashboards.
    """
    start = time.time()
    results: Dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        "version": "1.0.0",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "subsystems": {}
    }

    # 1. PostgreSQL
    try:
        from app.db.postgres import SessionLocal
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
        results["subsystems"]["postgresql"] = {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        results["subsystems"]["postgresql"] = {"status": "unhealthy", "error": str(e)}
        results["status"] = "degraded"

    # 2. Neo4j
    try:
        from app.db.neo4j_db import neo4j_client
        neo4j_client.connect()
        sess = neo4j_client.get_session()
        sess.run("RETURN 1 AS health")
        sess.close()
        results["subsystems"]["neo4j"] = {"status": "healthy"}
    except Exception as e:
        results["subsystems"]["neo4j"] = {"status": "unavailable", "error": str(e)}
        # Neo4j being down is degraded, not fatal
        if results["status"] == "healthy":
            results["status"] = "degraded"

    # 3. Task Queue
    try:
        from app.services.ingestion.task_queue import get_task_queue
        q = get_task_queue()
        results["subsystems"]["task_queue"] = {
            "status": "healthy",
            "backend": q.backend_name,
            "queue_length": q.get_queue_length()
        }
    except Exception as e:
        results["subsystems"]["task_queue"] = {"status": "unhealthy", "error": str(e)}

    # 4. Storage
    try:
        from app.services.evidence.storage_backend import get_storage_backend
        storage = get_storage_backend()
        results["subsystems"]["storage"] = {
            "status": "healthy",
            "backend": storage.backend_name
        }
    except Exception as e:
        results["subsystems"]["storage"] = {"status": "unhealthy", "error": str(e)}

    # 5. LLM Provider
    try:
        from app.services.copilot.llm_provider import get_llm_provider
        provider = get_llm_provider()
        results["subsystems"]["llm"] = {
            "status": "healthy",
            "provider": provider.provider_name,
            "model": getattr(provider, "model", "unknown"),
            "type": "REAL_LLM" if getattr(provider, "is_real_llm", False) else "LOCAL_FALLBACK"
        }
    except Exception as e:
        results["subsystems"]["llm"] = {"status": "unhealthy", "error": str(e)}

    # 6. Vector Backend & Native pgvector
    try:
        from app.services.rag.vector_backend import get_vector_status
        v_status = get_vector_status(db)
        s_code = v_status.get("status_code", "HEALTHY")
        
        if s_code == "HEALTHY":
            results["subsystems"]["vector_search"] = {
                "status": "healthy",
                "mode": "native" if v_status["active_backend"] == "pgvector" else "in_memory",
                "extension": v_status["native_pgvector_available"]
            }
            results["subsystems"]["pgvector"] = {
                "status": "healthy",
                "mode": "native" if v_status["active_backend"] == "pgvector" else "in_memory",
                "extension": v_status["native_pgvector_available"]
            }
        elif s_code == "DEGRADED_FALLBACK":
            results["subsystems"]["vector_search"] = {
                "status": "degraded",
                "mode": "in_memory_fallback",
                "extension": False,
                "reason": v_status.get("fallback_reason")
            }
            results["subsystems"]["pgvector"] = {
                "status": "degraded",
                "mode": "in_memory_fallback",
                "extension": False
            }
            if results["status"] == "healthy":
                results["status"] = "degraded"
        else: # PGVECTOR_REQUIRED_BUT_UNAVAILABLE
            results["subsystems"]["vector_search"] = {
                "status": "unhealthy",
                "mode": "pgvector_required_but_unavailable",
                "extension": False,
                "error": v_status.get("error")
            }
            results["subsystems"]["pgvector"] = {
                "status": "unhealthy",
                "mode": "pgvector_required_but_unavailable",
                "extension": False
            }
            results["status"] = "degraded"
    except Exception as e:
        results["subsystems"]["vector_search"] = {"status": "unhealthy", "error": str(e)}

    elapsed = round((time.time() - start) * 1000, 2)
    results["total_latency_ms"] = elapsed

    return results
