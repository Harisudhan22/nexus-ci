import uuid
import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.db.postgres import get_db
from app.core.dependencies import get_current_user
from app.models.models import User, SourceRecord, SourceJob, AuditLog
from app.services.adapters import get_adapter
from app.services.ingestion.coordinator import PipelineCoordinator
from app.services.rag.rag_service import RAGService
from app.api.websocket import ws_manager

router = APIRouter(prefix="/sync", tags=["sync"])

@router.post("/simulate/{source_type}")
async def simulate_live_sync_event(
    source_type: str,
    payload: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Simulates real-time multi-source pipeline ingestion emitting WebSocket milestones."""
    st = source_type.lower()
    adapter_name = "cctns" if st == "fir" else "cdr" if st == "cdr" else "financial" if st in ["tx", "transaction"] else "intelligence"
    adapter = get_adapter(adapter_name)

    data = payload or {}
    case_id = data.get("case_id", "case-101")
    
    # 1. NEW_RECORD
    job_id = f"job-{uuid.uuid4().hex[:8]}"
    job = SourceJob(
        id=job_id,
        source_adapter=adapter.adapter_name,
        source_record_id=f"REC-{uuid.uuid4().hex[:6]}",
        case_id=case_id,
        status="QUEUED",
        stage="INIT",
        progress=10
    )
    db.add(job)
    db.commit()

    await ws_manager.broadcast("NEW_RECORD_RECEIVED", {"jobId": job_id, "adapter": adapter.adapter_name, "caseId": case_id})

    # 2. PROCESSING_STARTED
    job.status = "PROCESSING"
    job.stage = "NORMALIZING"
    job.progress = 30
    db.commit()

    rec = adapter.normalize(data, case_id=case_id)

    src_rec = SourceRecord(
        id=f"rec-{uuid.uuid4().hex[:8]}",
        source_adapter=adapter.adapter_name,
        source_record_id=rec.source_record_id,
        record_type=rec.record_type,
        case_id=case_id,
        sha256=rec.sha256,
        status="processed",
        payload=rec.payload,
        parsed_entities=rec.extracted_entities,
        parsed_relationships=rec.extracted_relationships
    )
    db.add(src_rec)
    db.commit()

    await ws_manager.broadcast("ENTITIES_EXTRACTED", {"jobId": job_id, "entitiesCount": len(rec.extracted_entities)})

    # 3. HISTORICAL MATCH & CROSS-CASE LINK DETECTED
    await ws_manager.broadcast("HISTORICAL_MATCH_FOUND", {"jobId": job_id, "matchedEntity": "Ravi Kumar", "crossCaseIds": ["case-101", "case-205"]})
    await ws_manager.broadcast("POSTGRESQL_UPDATED", {"jobId": job_id, "tables": ["source_records", "canonical_entities", "entity_relationships"]})
    await ws_manager.broadcast("NEO4J_UPDATED", {"jobId": job_id, "nodesAdded": len(rec.extracted_entities), "edgesAdded": len(rec.extracted_relationships)})

    # 4. RAG INDEXING
    rag_svc = RAGService(db)
    sample_text = f"Simulated {rec.record_type} event ({rec.source_record_id}) ingested for case {case_id}. Payload: {rec.payload}"
    rag_svc.chunk_document(document_id=rec.source_record_id, case_id=case_id, text_content=sample_text, source_type=rec.record_type)

    await ws_manager.broadcast("RAG_INDEXED", {"jobId": job_id, "documentId": rec.source_record_id})

    # 5. COMPLETED
    job.status = "COMPLETED"
    job.stage = "DONE"
    job.progress = 100
    job.completed_at = datetime.datetime.utcnow()
    db.commit()

    await ws_manager.broadcast("PROCESSING_COMPLETED", {"jobId": job_id, "recordId": rec.source_record_id})

    return {
        "status": "success",
        "jobId": job_id,
        "recordId": rec.source_record_id,
        "message": f"Real-time pipeline completed for {rec.record_type} {rec.source_record_id}."
    }

@router.get("/jobs")
def list_sync_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists current background processing jobs."""
    jobs = db.query(SourceJob).order_by(SourceJob.started_at.desc()).limit(20).all()
    return [{"id": j.id, "adapter": j.source_adapter, "recordId": j.source_record_id, "caseId": j.case_id, "status": j.status, "stage": j.stage, "progress": j.progress, "startedAt": j.started_at.isoformat() if j.started_at else ""} for j in jobs]
