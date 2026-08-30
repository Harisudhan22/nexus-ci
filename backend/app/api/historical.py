import os
import json
import uuid
import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from app.db.postgres import get_db
from app.db.neo4j_db import get_neo4j
from app.core.dependencies import get_current_user
from app.models.models import (
    User, Case, Document, CanonicalEntity, EntityRelationship,
    SourceRecord, Finding, AuditLog, RawMention
)
from app.services.adapters import ADAPTERS, get_adapter
from app.services.graph.graph_service import Neo4jGraphService
from app.services.ingestion.coordinator import PipelineCoordinator

router = APIRouter(prefix="/historical", tags=["historical"])

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "historical"))

def _source_count(db: Session, document_types: list[str], record_types: list[str]) -> int:
    doc_count = db.query(Document).filter(Document.source_type.in_(document_types)).count()
    record_count = db.query(SourceRecord).filter(SourceRecord.record_type.in_(record_types)).count()
    return doc_count + record_count

@router.get("/stats")
def get_historical_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns real database-derived counts for the Historical Intelligence subsystem."""
    total_cases = db.query(Case).count()
    total_entities = db.query(CanonicalEntity).count()
    total_docs = db.query(Document).count()
    total_relationships = db.query(EntityRelationship).count()
    total_findings = db.query(Finding).count()

    # Category counts
    fir_count = _source_count(db, ["FIR", "POLICE", "POLICE_REPORT"], ["FIR"])
    cdr_count = _source_count(db, ["CDR"], ["CDR"])
    fin_count = _source_count(db, ["TRANSACTION", "TRANSACTIONS"], ["TRANSACTION", "TRANSACTIONS"])
    surv_count = _source_count(db, ["SURVEILLANCE"], ["SURVEILLANCE"])
    intel_count = _source_count(db, ["INTELLIGENCE", "INTEL_REPORT"], ["INTELLIGENCE", "INTEL_REPORT"])
    failures_count = db.query(Document).filter(Document.processing_status == "failed").count()

    # Entity types
    persons = db.query(CanonicalEntity).filter(CanonicalEntity.type == "person").count()
    phones = db.query(CanonicalEntity).filter(CanonicalEntity.type == "phone").count()
    vehicles = db.query(CanonicalEntity).filter(CanonicalEntity.type == "vehicle").count()
    locations = db.query(CanonicalEntity).filter(CanonicalEntity.type == "location").count()
    orgs = db.query(CanonicalEntity).filter(CanonicalEntity.type == "org").count()
    accounts = db.query(CanonicalEntity).filter(CanonicalEntity.type == "account").count()

    indexed_rag_documents = db.query(Document).filter(Document.processing_status == "completed").count()

    return {
        "historicalCases": total_cases,
        "firRecords": fir_count,
        "cdrRecords": cdr_count,
        "financialRecords": fin_count,
        "surveillanceRecords": surv_count,
        "intelligenceRecords": intel_count,
        "persons": persons,
        "phones": phones,
        "vehicles": vehicles,
        "locations": locations,
        "organizations": orgs,
        "accounts": accounts,
        "documents": total_docs,
        "entities": total_entities,
        "relationships": total_relationships,
        "evidence": total_docs,
        "indexedRagDocuments": indexed_rag_documents,
        "processingFailures": failures_count
    }

@router.get("/sources")
def list_data_sources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns the list and live status of all source adapters."""
    sources_meta = [
        {"id": "src-cctns", "name": "Mock CCTNS Adapter", "category": "FIR / Police Reports", "status": "Ready", "mode": "Adapter Bridge", "records": _source_count(db, ["FIR"], ["FIR"])},
        {"id": "src-police", "name": "Mock State Police Adapter", "category": "Police Reports", "status": "Ready", "mode": "Direct Ingestion", "records": _source_count(db, ["POLICE", "POLICE_REPORT"], ["POLICE", "POLICE_REPORT"])},
        {"id": "src-cdr", "name": "Mock CDR Adapter", "category": "Call Detail Records", "status": "Ready", "mode": "Stream Parser", "records": _source_count(db, ["CDR"], ["CDR"])},
        {"id": "src-fin", "name": "Mock Financial Adapter", "category": "Bank & Hawala Transactions", "status": "Ready", "mode": "Ledger Ingestion", "records": _source_count(db, ["TRANSACTION", "TRANSACTIONS"], ["TRANSACTION", "TRANSACTIONS"])},
        {"id": "src-srv", "name": "Mock Surveillance Adapter", "category": "CCTV & Field Observations", "status": "Ready", "mode": "Event Log Parser", "records": _source_count(db, ["SURVEILLANCE"], ["SURVEILLANCE"])},
        {"id": "src-dossier", "name": "Mock Criminal History Adapter", "category": "Criminal Dossiers", "status": "Ready", "mode": "Profile Sync", "records": _source_count(db, ["DOSSIER", "CRIMINAL_HISTORY"], ["DOSSIER", "CRIMINAL_HISTORY"])},
        {"id": "src-intel", "name": "Mock Intelligence Adapter", "category": "Special Branch Intelligence", "status": "Ready", "mode": "Bulletin Ingestion", "records": _source_count(db, ["INTELLIGENCE", "INTEL_REPORT"], ["INTELLIGENCE", "INTEL_REPORT"])},
        {"id": "src-social", "name": "Mock Social Intelligence Adapter", "category": "Social Media OSINT", "status": "Ready", "mode": "OSINT Scraper", "records": _source_count(db, ["SOCIAL", "SOCIAL_INTEL"], ["SOCIAL", "SOCIAL_INTEL"])},
        {"id": "src-veh", "name": "Mock Vehicle Adapter", "category": "RTO & Toll Registrations", "status": "Ready", "mode": "Registry Sync", "records": _source_count(db, ["VEHICLE", "VEHICLE_RECORD"], ["VEHICLE", "VEHICLE_RECORD"])},
    ]
    return sources_meta

@router.post("/import-batch")
def import_historical_batch(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    neo4j_sess = Depends(get_neo4j)
):
    """Runs batch import across all synthetic datasets in data/historical."""
    from scripts.seed_historical import seed_all
    seed_all()
    
    # Audit log
    audit = AuditLog(
        id=f"aud-{uuid.uuid4().hex[:8]}",
        user_id=current_user.id,
        action="SYNC",
        resource="Historical Batch Ingestion",
        result="success"
    )
    db.add(audit)
    db.commit()

    return {"status": "success", "message": "Historical batch imported and indexed into PostgreSQL and Neo4j."}

@router.post("/demo-reset")
def reset_sih_demo_mode(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resets the synthetic SIH demonstration dataset cleanly without affecting user accounts."""
    if current_user.role.lower() not in ["admin", "supervisor", "investigator", "senior_investigator", "analyst"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    from scripts.seed_historical import seed_all
    seed_all()

    audit = AuditLog(
        id=f"aud-{uuid.uuid4().hex[:8]}",
        user_id=current_user.id,
        action="DEMO_RESET",
        resource="SIH Demonstration Dataset Reset",
        result="success"
    )
    db.add(audit)
    db.commit()

    stats = get_historical_stats(current_user=current_user, db=db)

    return {
        "status": "success",
        "message": (
            "SIH Demonstration Mode re-initialized successfully. "
            f"{stats['historicalCases']} cases, {stats['entities']} entities, "
            f"{stats['relationships']} relationships, and {stats['evidence']} evidence files active."
        )
    }

@router.post("/simulate/fir")
def simulate_fir(
    fir_data: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Simulates a live FIR arriving from CCTNS adapter."""
    adapter = get_adapter("cctns")
    payload = fir_data or {
        "fir_no": f"FIR-SIM-{uuid.uuid4().hex[:4]}",
        "case_id": "case-101",
        "police_station": "Central Station PS",
        "date": datetime.datetime.utcnow().isoformat(),
        "suspects": [{"name": "R. Kumar", "role": "suspect", "phone": "9876543210", "vehicle": "TN01AB1234"}],
        "complaint_text": "Real-time patrol alert: Subject R. Kumar driving TN01AB1234 observed in suspicious vicinity."
    }
    
    record = adapter.normalize(payload, case_id=payload.get("case_id", "case-101"))
    
    # Store source record
    src_rec = SourceRecord(
        id=f"rec-{uuid.uuid4().hex[:8]}",
        source_adapter=adapter.adapter_name,
        source_record_id=record.source_record_id,
        record_type=record.record_type,
        case_id=record.case_id,
        sha256=record.sha256,
        status="processed",
        payload=record.payload,
        parsed_entities=record.extracted_entities
    )
    db.add(src_rec)
    db.commit()

    return {
        "status": "success",
        "recordId": src_rec.id,
        "sourceRecordId": record.source_record_id,
        "message": f"Real-time FIR {record.source_record_id} ingested and validated via MockCCTNSAdapter."
    }

@router.post("/simulate/cdr")
def simulate_cdr(
    cdr_data: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Simulates a live CDR call event."""
    adapter = get_adapter("cdr")
    payload = cdr_data or {
        "call_id": f"CDR-SIM-{uuid.uuid4().hex[:4]}",
        "case_id": "case-101",
        "caller": "9876543210",
        "callee": "9876543211",
        "duration": 420,
        "cell_tower": "Central Station Tower",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    record = adapter.normalize(payload, case_id=payload.get("case_id", "case-101"))
    
    src_rec = SourceRecord(
        id=f"rec-{uuid.uuid4().hex[:8]}",
        source_adapter=adapter.adapter_name,
        source_record_id=record.source_record_id,
        record_type=record.record_type,
        case_id=record.case_id,
        sha256=record.sha256,
        status="processed",
        payload=record.payload,
        parsed_entities=record.extracted_entities,
        parsed_relationships=record.extracted_relationships
    )
    db.add(src_rec)
    db.commit()

    return {
        "status": "success",
        "recordId": src_rec.id,
        "sourceRecordId": record.source_record_id,
        "message": f"Real-time CDR {record.source_record_id} ingested via MockCDRAdapter."
    }

@router.post("/simulate/transaction")
def simulate_transaction(
    tx_data: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Simulates a live financial transaction event."""
    adapter = get_adapter("financial")
    payload = tx_data or {
        "tx_id": f"TX-SIM-{uuid.uuid4().hex[:4]}",
        "case_id": "case-205",
        "sender_account": "A101",
        "receiver_account": "A201",
        "amount": 350000,
        "currency": "INR",
        "bank": "State Bank of India",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    record = adapter.normalize(payload, case_id=payload.get("case_id", "case-205"))
    
    src_rec = SourceRecord(
        id=f"rec-{uuid.uuid4().hex[:8]}",
        source_adapter=adapter.adapter_name,
        source_record_id=record.source_record_id,
        record_type=record.record_type,
        case_id=record.case_id,
        sha256=record.sha256,
        status="processed",
        payload=record.payload,
        parsed_entities=record.extracted_entities,
        parsed_relationships=record.extracted_relationships
    )
    db.add(src_rec)
    db.commit()

    return {
        "status": "success",
        "recordId": src_rec.id,
        "sourceRecordId": record.source_record_id,
        "message": f"Real-time Transaction {record.source_record_id} ingested via MockFinancialAdapter."
    }
