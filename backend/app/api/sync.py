import uuid
import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.db.postgres import get_db
from app.db.neo4j_db import get_neo4j
from app.core.dependencies import get_current_user, verify_case_access
from app.models.models import User, SourceRecord, SourceJob, AuditLog, CanonicalEntity
from app.services.adapters import get_adapter
from app.services.rag.rag_service import RAGService
from app.services.graph.graph_service import Neo4jGraphService
from app.services.patterns.findings_service import FindingsEngine
from app.api.websocket import ws_manager

router = APIRouter(prefix="/sync", tags=["sync"])

@router.post("/simulate/{source_type}")
async def simulate_live_sync_event(
    source_type: str,
    payload: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    neo4j_sess = Depends(get_neo4j)
):
    """Simulates real-time multi-source pipeline ingestion emitting WebSocket milestones."""
    st = source_type.lower()
    adapter_name = "cctns" if st == "fir" else "cdr" if st == "cdr" else "financial" if st in ["tx", "transaction"] else "intelligence"
    adapter = get_adapter(adapter_name)

    data = payload or {}
    case_id = data.get("case_id", "case-101")
    if not verify_case_access(current_user, case_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    
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
    await ws_manager.broadcast("PROCESSING_STARTED", {"jobId": job_id, "stage": job.stage, "progress": job.progress})

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

    graph_svc = Neo4jGraphService(neo4j_sess, db)
    canonical_by_surface: dict[tuple[str, str], CanonicalEntity] = {}
    for entity in rec.extracted_entities:
        surface = str(entity.get("surface") or "").strip()
        entity_type = str(entity.get("type") or "person").strip().lower()
        if not surface:
            continue
        canonical = db.query(CanonicalEntity).filter(
            CanonicalEntity.label == surface,
            CanonicalEntity.type == entity_type
        ).first()
        if canonical:
            case_ids = list(canonical.case_ids or [])
            if case_id not in case_ids:
                canonical.case_ids = case_ids + [case_id]
        else:
            canonical = CanonicalEntity(
                id=f"ent-{uuid.uuid4().hex[:8]}",
                type=entity_type,
                label=surface,
                subtitle=str(entity.get("role") or rec.record_type),
                case_ids=[case_id],
                aliases=[surface],
                relevance=60,
                attributes={k: v for k, v in entity.items() if k not in ["type", "surface"]},
                cluster=f"cluster_{len(surface) % 3 + 1}",
                x=float(100 + (len(surface) * 17) % 700),
                y=float(100 + (len(surface) * 23) % 420),
            )
            db.add(canonical)
        canonical_by_surface[(entity_type, surface)] = canonical
    db.commit()

    for canonical in canonical_by_surface.values():
        graph_svc.create_entity_node(
            entity_id=canonical.id,
            entity_type=canonical.type,
            label=canonical.label,
            case_ids=canonical.case_ids,
            cluster=canonical.cluster,
            properties=canonical.attributes,
        )

    created_relationships = 0
    for rel in rec.extracted_relationships:
        source_type = str(rel.get("source_type") or "person").lower()
        target_type = str(rel.get("target_type") or "person").lower()
        source = canonical_by_surface.get((source_type, str(rel.get("source", "")).strip()))
        target = canonical_by_surface.get((target_type, str(rel.get("target", "")).strip()))
        if not source or not target:
            continue
        props = dict(rel.get("properties") or {})
        props.update({
            "evidence_ids": [src_rec.id],
            "source": adapter.adapter_name,
            "created_by_pipeline": "Live Sync Adapter",
            "rationale": f"{rec.record_type} adapter extracted {rel.get('rel_type')} relationship from source record {rec.source_record_id}.",
        })
        graph_svc.create_relationship(
            source_id=source.id,
            source_type=source.type,
            target_id=target.id,
            target_type=target.type,
            rel_type=str(rel.get("rel_type") or "ASSOCIATED_WITH"),
            properties=props,
            case_ids=[case_id],
        )
        created_relationships += 1

    job.stage = "GRAPH_UPDATED"
    job.progress = 65
    db.commit()

    await ws_manager.broadcast("PROCESSING_PROGRESS", {"jobId": job_id, "stage": job.stage, "progress": job.progress})
    await ws_manager.broadcast("ENTITIES_EXTRACTED", {"jobId": job_id, "entitiesCount": len(rec.extracted_entities)})

    # 3. HISTORICAL MATCH & CROSS-CASE LINK DETECTED
    matched_cross_case = [
        entity.label
        for entity in canonical_by_surface.values()
        if len(entity.case_ids or []) > 1
    ]
    await ws_manager.broadcast("HISTORICAL_MATCH_FOUND", {"jobId": job_id, "matchedEntities": matched_cross_case})
    await ws_manager.broadcast("CROSS_CASE_LINK_DETECTED", {"jobId": job_id, "matchedEntities": matched_cross_case})
    await ws_manager.broadcast("POSTGRESQL_UPDATED", {"jobId": job_id, "tables": ["source_records", "canonical_entities", "entity_relationships"]})
    await ws_manager.broadcast("NEO4J_UPDATED", {"jobId": job_id, "nodesAdded": len(canonical_by_surface), "edgesAdded": created_relationships})

    # 4. RAG INDEXING
    rag_svc = RAGService(db)
    sample_text = f"Simulated {rec.record_type} event ({rec.source_record_id}) ingested for case {case_id}. Payload: {rec.payload}"
    rag_svc.chunk_document(document_id=rec.source_record_id, case_id=case_id, text_content=sample_text, source_type=rec.record_type)

    await ws_manager.broadcast("RAG_INDEXED", {"jobId": job_id, "documentId": rec.source_record_id})
    findings = FindingsEngine(db, neo4j_sess).analyze_case(case_id)
    await ws_manager.broadcast("ANALYTICS_UPDATED", {"jobId": job_id, "caseId": case_id})
    await ws_manager.broadcast("FINDING_CREATED", {"jobId": job_id, "count": len(findings)})

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
