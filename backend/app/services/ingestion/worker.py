"""
NEXUS-CI Background Worker — Production
=========================================
Dedicated worker daemon that polls the task queue and processes jobs
OUTSIDE the FastAPI request-response cycle.

Usage (Windows local):
    backend\\venv\\Scripts\\python.exe -m app.services.ingestion.worker

Usage (Docker):
    python -m app.services.ingestion.worker

For production: run as a SEPARATE PROCESS / container alongside the FastAPI app.

Features:
  - Heartbeat published every HEARTBEAT_INTERVAL seconds
  - Bounded retry (RETRYABLE exceptions vs permanent failures)
  - Graceful shutdown on SIGINT / SIGTERM
  - Structured logging with job_id, worker_id, stage, duration
"""
import os
import sys
import time
import uuid
import signal
import datetime
import threading
import traceback
from typing import Optional

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.services.ingestion.task_queue import (
    get_task_queue,
    TaskPayload,
    TaskStatus,
)

# ── Constants ─────────────────────────────────────────────────────────────────
WORKER_ID          = f"worker-{uuid.uuid4().hex[:8]}"
HEARTBEAT_INTERVAL = int(os.getenv("WORKER_HEARTBEAT_INTERVAL", "10"))   # seconds
POLL_INTERVAL      = float(os.getenv("WORKER_POLL_INTERVAL", "1.0"))     # seconds
MAX_RETRIES_DEFAULT = int(os.getenv("WORKER_MAX_RETRIES", "3"))

# Exception types that are RETRYABLE (transient failures)
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)

_shutdown_event = threading.Event()


def _log(job_id: str, stage: str, msg: str, level: str = "INFO") -> None:
    ts = datetime.datetime.now(datetime.UTC).isoformat()
    print(f"[{level}] {ts} worker={WORKER_ID} job={job_id} stage={stage} | {msg}")


def _handle_signal(signum, frame):
    print(f"\n[WORKER] Signal {signum} received — shutting down gracefully ...")
    _shutdown_event.set()


def _is_retryable(exc: Exception) -> bool:
    """Returns True for transient failures that should be retried."""
    return isinstance(exc, RETRYABLE_EXCEPTIONS)


# ── Job Handlers ──────────────────────────────────────────────────────────────

def _handle_health_check(task: TaskPayload, queue) -> None:
    """Harmless health-check job to verify the end-to-end queue pipeline."""
    _log(task.task_id, "health_check", "Running health-check job")
    from app.db.postgres import SessionLocal
    db = SessionLocal()
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        _log(task.task_id, "health_check", "PostgreSQL ping OK")
    finally:
        db.close()
    queue.update_status(task.task_id, TaskStatus.COMPLETED, worker_id=WORKER_ID)
    _log(task.task_id, "health_check", "COMPLETED")


def _handle_document_processing(task: TaskPayload, queue) -> None:
    from app.db.postgres import SessionLocal
    from app.db.neo4j_db import get_neo4j_session

    doc_id = task.payload.get("document_id")
    if not doc_id:
        raise ValueError("Missing document_id in task payload")

    db = SessionLocal()
    neo4j_sess = None
    try:
        try:
            neo4j_sess = get_neo4j_session()
        except Exception as e:
            _log(task.task_id, "neo4j_connect", f"Neo4j unavailable ({e}), continuing without graph sync")

        from app.services.ingestion.coordinator import PipelineCoordinator
        coordinator = PipelineCoordinator(db, neo4j_sess)

        _log(task.task_id, "pipeline", f"Processing document {doc_id}")
        t0 = time.monotonic()
        success = coordinator.process_document(doc_id)
        duration_ms = round((time.monotonic() - t0) * 1000, 1)

        if success:
            queue.update_status(task.task_id, TaskStatus.COMPLETED, worker_id=WORKER_ID)
            _log(task.task_id, "pipeline", f"COMPLETED in {duration_ms}ms")
        else:
            queue.update_status(
                task.task_id, TaskStatus.FAILED,
                error=f"Pipeline returned False for {doc_id}",
                worker_id=WORKER_ID,
            )
            _log(task.task_id, "pipeline", f"FAILED (pipeline returned False)", level="WARN")
    finally:
        db.close()
        if neo4j_sess:
            try:
                neo4j_sess.close()
            except Exception:
                pass


def _handle_reindex(task: TaskPayload, queue) -> None:
    from app.db.postgres import SessionLocal
    from app.services.rag.rag_service import RAGService
    from app.models.models import Document

    case_id = task.payload.get("case_id")
    db = SessionLocal()
    try:
        docs_query = db.query(Document)
        if case_id:
            docs_query = docs_query.filter(Document.case_id == case_id)

        rag = RAGService(db)
        count = 0
        for doc in docs_query.all():
            if doc.extracted_text:
                rag.chunk_document(doc.id, doc.case_id, doc.extracted_text, source_type=doc.source_type)
                count += 1

        queue.update_status(task.task_id, TaskStatus.COMPLETED, worker_id=WORKER_ID)
        _log(task.task_id, "reindex", f"COMPLETED — {count} documents reindexed" + (f" for case {case_id}" if case_id else ""))
    finally:
        db.close()


def _handle_analytics(task: TaskPayload, queue) -> None:
    from app.db.postgres import SessionLocal
    from app.db.neo4j_db import get_neo4j_session
    from app.services.patterns.findings_service import FindingsEngine

    case_id = task.payload.get("case_id")
    if not case_id:
        raise ValueError("Missing case_id in analytics task payload")

    db = SessionLocal()
    neo4j_sess = None
    try:
        try:
            neo4j_sess = get_neo4j_session()
        except Exception:
            pass

        engine = FindingsEngine(db, neo4j_sess)
        engine.analyze_case(case_id)

        queue.update_status(task.task_id, TaskStatus.COMPLETED, worker_id=WORKER_ID)
        _log(task.task_id, "analytics", f"COMPLETED for case {case_id}")
    finally:
        db.close()
        if neo4j_sess:
            try:
                neo4j_sess.close()
            except Exception:
                pass


# ── Task Router ───────────────────────────────────────────────────────────────

HANDLERS = {
    "health_check":         _handle_health_check,
    "document_processing":  _handle_document_processing,
    "reindex":              _handle_reindex,
    "analytics":            _handle_analytics,
}


def process_task(task: TaskPayload) -> None:
    """
    Routes a dequeued task to the appropriate handler with bounded retry logic.
    """
    queue = get_task_queue()
    queue.update_status(task.task_id, TaskStatus.PROCESSING, worker_id=WORKER_ID)
    _log(task.task_id, "dispatch", f"task_type={task.task_type} retry={task.retry_count}/{task.max_retries}")

    handler = HANDLERS.get(task.task_type)
    if handler is None:
        err = f"Unknown task type: {task.task_type}"
        queue.update_status(task.task_id, TaskStatus.FAILED, error=err, worker_id=WORKER_ID)
        _log(task.task_id, "dispatch", err, level="ERROR")
        return

    try:
        handler(task, queue)
    except Exception as exc:
        retry_count = task.retry_count + 1
        max_retries = task.max_retries if task.max_retries is not None else MAX_RETRIES_DEFAULT

        if _is_retryable(exc) and retry_count <= max_retries:
            task.retry_count = retry_count
            queue.update_status(task.task_id, TaskStatus.RETRYING, error=str(exc), worker_id=WORKER_ID)
            _log(task.task_id, "retry", f"Retryable error (attempt {retry_count}/{max_retries}): {exc}", level="WARN")
            # Re-queue for retry
            task.status = TaskStatus.QUEUED
            queue.enqueue(task)
        else:
            err_detail = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-800:]}"
            queue.update_status(task.task_id, TaskStatus.FAILED, error=str(exc)[:500], worker_id=WORKER_ID)
            _log(task.task_id, "failed", f"FAILED permanently: {err_detail}", level="ERROR")


# ── Heartbeat Thread ──────────────────────────────────────────────────────────

def _heartbeat_loop() -> None:
    """Publishes worker heartbeat on a background thread until shutdown."""
    queue = get_task_queue()
    while not _shutdown_event.is_set():
        try:
            queue.publish_heartbeat(WORKER_ID)
        except Exception as exc:
            print(f"[WARN] Heartbeat publish failed: {exc}")
        _shutdown_event.wait(timeout=HEARTBEAT_INTERVAL)


# ── Main Worker Loop ──────────────────────────────────────────────────────────

def run_worker(poll_interval: float = POLL_INTERVAL, max_iterations: Optional[int] = None) -> int:
    """
    Main worker loop.

    Args:
        poll_interval: Seconds between queue polls when queue is empty.
        max_iterations: Maximum tasks to process before exiting (None = infinite).

    Returns:
        Number of tasks processed.
    """
    signal.signal(signal.SIGINT, _handle_signal)
    try:
        signal.signal(signal.SIGTERM, _handle_signal)
    except (OSError, ValueError):
        pass   # Windows may not support SIGTERM in all contexts

    queue = get_task_queue()
    print(f"[WORKER] Started — id={WORKER_ID} backend={queue.backend_name} poll={poll_interval}s")

    # Start heartbeat thread
    hb_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    hb_thread.start()

    processed = 0
    try:
        while not _shutdown_event.is_set():
            if max_iterations is not None and processed >= max_iterations:
                print(f"[WORKER] Reached max_iterations={max_iterations}, stopping.")
                break

            task = queue.dequeue(timeout=int(max(1, poll_interval)))
            if task:
                process_task(task)
                processed += 1
            else:
                _shutdown_event.wait(timeout=poll_interval)
    finally:
        # Graceful shutdown: flush heartbeat as offline
        try:
            queue.publish_heartbeat(WORKER_ID + ":shutdown")
        except Exception:
            pass
        print(f"[WORKER] Stopped. Processed {processed} tasks.")

    return processed


if __name__ == "__main__":
    run_worker()
