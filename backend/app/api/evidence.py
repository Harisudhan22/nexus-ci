import os
import uuid
import datetime
import hashlib
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.db.postgres import get_db
from app.db.neo4j_db import get_neo4j
from app.core.dependencies import get_current_user, verify_case_access
from app.models.models import Document, User, RawMention, Case, AuditLog
from app.services.ingestion.coordinator import PipelineCoordinator
from app.schemas.evidence import EvidenceResponse, IntegrityVerificationResponse

router = APIRouter(tags=["evidence"])

ALLOWED_EXTENSIONS = {"pdf", "docx", "csv", "json", "png", "jpg", "jpeg", "txt", "log"}
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB

def validate_file(filename: str, size: int):
    # Extension validation
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension: {ext}. Allowed: {ALLOWED_EXTENSIONS}"
        )
    # Size validation
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of 15MB (got {size / (1024 * 1024):.1f}MB)"
        )

@router.post("/cases/{case_id}/documents", response_model=EvidenceResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_document(
    case_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_type: str = Form("JSON"), # Default fallback
    title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    neo4j_sess = Depends(get_neo4j)
):
    # Verify case access
    if not verify_case_access(current_user, case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this case.")

    # Check case exists
    db_case = db.query(Case).filter(Case.id == case_id).first()
    if not db_case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    # In-memory size validation first (UploadFile might not expose size, so we read it)
    contents = file.file.read()
    file_size = len(contents)
    file.file.seek(0) # Reset pointer
    
    validate_file(file.filename, file_size)

    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    clean_filename = "".join(c for c in file.filename if c.isalnum() or c in ".-_ ")
    storage_dir = os.path.join("./uploads", case_id)
    os.makedirs(storage_dir, exist_ok=True)
    storage_path = os.path.join(storage_dir, f"{doc_id}-{clean_filename}")

    with open(storage_path, "wb") as f:
        f.write(contents)

    sha256 = hashlib.sha256(contents).hexdigest()

    doc = Document(
        id=doc_id,
        case_id=case_id,
        filename=file.filename,
        source_type=source_type,
        storage_path=storage_path,
        sha256=sha256,
        size_bytes=file_size,
        uploaded_by=current_user.id,
        uploaded_at=datetime.datetime.utcnow(),
        processing_status="queued",
        processing_error=None
    )
    db.add(doc)

    audit = AuditLog(
        id=f"audit-{uuid.uuid4().hex[:8]}",
        timestamp=datetime.datetime.utcnow(),
        user_id=current_user.id,
        action="UPLOAD",
        case_id=case_id,
        resource=f"Document {file.filename}",
        result="success"
    )
    db.add(audit)
    db.commit()

    background_tasks.add_task(_run_pipeline, doc_id)

    return {
        "id": doc.id,
        "caseId": doc.case_id,
        "title": title or doc.filename,
        "sourceType": doc.source_type,
        "fileName": doc.filename,
        "sha256": doc.sha256,
        "uploadedAt": doc.uploaded_at.isoformat() + "Z",
        "uploadedBy": doc.uploaded_by,
        "sizeBytes": doc.size_bytes,
        "status": "processing",
        "relevance": 50,
        "entityMentions": []
    }


def _run_pipeline(doc_id: str):
    """Background task with its own DB + Neo4j sessions."""
    from app.db.postgres import SessionLocal
    from app.db.neo4j_db import neo4j_client
    db = SessionLocal()
    neo4j_sess = None
    try:
        neo4j_client.connect()
        neo4j_sess = neo4j_client.get_session()
    except Exception:
        pass
    try:
        coordinator = PipelineCoordinator(db, neo4j_sess)
        coordinator.process_document(doc_id)
    finally:
        db.close()
        if neo4j_sess:
            neo4j_sess.close()


@router.get("/cases/{case_id}/documents", response_model=List[EvidenceResponse])
def list_case_documents(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_case_access(current_user, case_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    
    docs = db.query(Document).filter(Document.case_id == case_id).all()
    results = []
    for doc in docs:
        results.append({
            "id": doc.id,
            "caseId": doc.case_id,
            "title": doc.filename,
            "sourceType": doc.source_type,
            "fileName": doc.filename,
            "sha256": doc.sha256,
            "uploadedAt": doc.uploaded_at.isoformat() + "Z" if doc.uploaded_at else "",
            "uploadedBy": doc.uploaded_by,
            "sizeBytes": doc.size_bytes,
            "status": "processed" if doc.processing_status == "completed" else ("failed" if doc.processing_status == "failed" else "processing"),
            "relevance": 75 if doc.processing_status == "completed" else 0,
            "entityMentions": []
        })
    return results

@router.get("/documents/{id}", response_model=EvidenceResponse)
def get_document(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence document not found.")
        
    if not verify_case_access(current_user, doc.case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this document's case.")

    # Get entity mentions
    mentions = db.query(RawMention).filter(RawMention.evidence_id == id).all()
    mention_ids = list(set([m.resolved_to for m in mentions if m.resolved_to]))

    # Map status
    status_mapped = "processed" if doc.processing_status == "completed" else ("failed" if doc.processing_status == "failed" else "processing")

    return {
        "id": doc.id,
        "caseId": doc.case_id,
        "title": doc.filename,
        "sourceType": doc.source_type,
        "fileName": doc.filename,
        "sha256": doc.sha256,
        "uploadedAt": doc.uploaded_at.isoformat(),
        "uploadedBy": doc.uploaded_by,
        "sizeBytes": doc.size_bytes,
        "status": status_mapped,
        "relevance": 75 if doc.processing_status == "completed" else 0,
        "extractedText": doc.extracted_text,
        "rows": doc.rows_data,
        "entityMentions": mention_ids
    }

@router.get("/documents/{id}/text")
def get_document_text(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not verify_case_access(current_user, doc.case_id):
        raise HTTPException(status_code=403, detail="Access denied.")
    return {"id": doc.id, "text": doc.extracted_text or ""}

@router.get("/documents/{id}/entities")
def get_document_entities(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not verify_case_access(current_user, doc.case_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    mentions = db.query(RawMention).filter(RawMention.evidence_id == id).all()
    return [{"id": m.id, "surface": m.surface, "type": m.type, "resolvedTo": m.resolved_to} for m in mentions]

@router.post("/documents/{id}/verify-integrity", response_model=IntegrityVerificationResponse)
def verify_document_integrity(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if not verify_case_access(current_user, doc.case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    if not os.path.exists(doc.storage_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file missing on server filesystem.")

    # Recompute SHA-256
    sha256_hash = hashlib.sha256()
    with open(doc.storage_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    recalculated = sha256_hash.hexdigest()

    verified = (recalculated == doc.sha256)
    
    # Audit action
    audit = AuditLog(
        id=f"audit-{uuid.uuid4().hex[:8]}",
        timestamp=datetime.datetime.utcnow(),
        user_id=current_user.id,
        action="VIEW",
        case_id=doc.case_id,
        resource=f"Document Integrity Check {doc.filename} (Match: {verified})",
        result="success" if verified else "failed"
    )
    db.add(audit)
    db.commit()

    message = "Current file content matches the recorded SHA-256 hash." if verified else "Integrity breach: recalculated hash does not match original."
    return {
        "verified": verified,
        "message": message,
        "sha256": recalculated
    }

@router.get("/documents/{id}/versions")
def list_document_versions(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all historical versions of a document."""
    from app.models.models import DocumentVersion
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not verify_case_access(current_user, doc.case_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    versions = db.query(DocumentVersion).filter(DocumentVersion.document_id == id).order_by(DocumentVersion.version_number.desc()).all()
    return [{
        "id": v.id,
        "documentId": v.document_id,
        "versionNumber": v.version_number,
        "sha256": v.sha256,
        "uploaderId": v.uploader_id,
        "changeReason": v.change_reason or "Update",
        "createdAt": v.created_at.isoformat() if v.created_at else ""
    } for v in versions]

@router.post("/documents/{id}/versions")
def upload_document_version(
    id: str,
    file: UploadFile = File(...),
    change_reason: str = Form("Document revision"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Uploads a new version of a document, preserving SHA-256 integrity and historical provenance."""
    from app.models.models import DocumentVersion
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not verify_case_access(current_user, doc.case_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    contents = file.file.read()
    validate_file(file.filename, len(contents))
    sha256 = hashlib.sha256(contents).hexdigest()
    
    current_versions = db.query(DocumentVersion).filter(DocumentVersion.document_id == id).count()
    if current_versions == 0:
        baseline_version = DocumentVersion(
            id=f"ver-{uuid.uuid4().hex[:8]}",
            document_id=id,
            version_number=1,
            sha256=doc.sha256,
            storage_path=doc.storage_path,
            uploader_id=doc.uploaded_by,
            change_reason="Original upload",
            created_at=doc.uploaded_at or datetime.datetime.utcnow()
        )
        db.add(baseline_version)
        current_versions = 1

    new_version_num = current_versions + 1

    clean_filename = "".join(c for c in file.filename if c.isalnum() or c in ".-_ ")
    storage_dir = os.path.join("./uploads", doc.case_id)
    os.makedirs(storage_dir, exist_ok=True)
    version_path = os.path.join(storage_dir, f"{doc.id}-v{new_version_num}-{clean_filename}")

    with open(version_path, "wb") as f:
        f.write(contents)

    # Save version record
    ver_obj = DocumentVersion(
        id=f"ver-{uuid.uuid4().hex[:8]}",
        document_id=id,
        version_number=new_version_num,
        sha256=sha256,
        storage_path=version_path,
        uploader_id=current_user.id,
        change_reason=change_reason,
        created_at=datetime.datetime.utcnow()
    )
    db.add(ver_obj)

    # Update document header
    doc.sha256 = sha256
    doc.storage_path = version_path
    doc.size_bytes = len(contents)

    audit = AuditLog(
        id=f"audit-{uuid.uuid4().hex[:8]}",
        timestamp=datetime.datetime.utcnow(),
        user_id=current_user.id,
        action="UPLOAD",
        case_id=doc.case_id,
        resource=f"Document {doc.filename} Version {new_version_num} uploaded ({change_reason})",
        result="success"
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "versionId": ver_obj.id,
        "versionNumber": new_version_num,
        "sha256": sha256
    }

@router.get("/documents/{id}/versions/{version_id}")
def get_document_version(
    id: str,
    version_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns metadata for one stored document version."""
    from app.models.models import DocumentVersion
    doc = db.query(Document).filter(Document.id == id).first()
    version = db.query(DocumentVersion).filter(
        DocumentVersion.id == version_id,
        DocumentVersion.document_id == id
    ).first()
    if not doc or not version:
        raise HTTPException(status_code=404, detail="Document or Version not found.")
    if not verify_case_access(current_user, doc.case_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    return {
        "id": version.id,
        "documentId": version.document_id,
        "versionNumber": version.version_number,
        "sha256": version.sha256,
        "storagePath": version.storage_path,
        "uploaderId": version.uploader_id,
        "changeReason": version.change_reason,
        "createdAt": version.created_at.isoformat() if version.created_at else ""
    }

@router.post("/documents/{id}/versions/{version_id}/restore")
def restore_document_version(
    id: str,
    version_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Restores a previous document version cleanly without destroying history."""
    from app.models.models import DocumentVersion
    doc = db.query(Document).filter(Document.id == id).first()
    target_ver = db.query(DocumentVersion).filter(DocumentVersion.id == version_id, DocumentVersion.document_id == id).first()
    if not doc or not target_ver:
        raise HTTPException(status_code=404, detail="Document or Version not found.")
    if not verify_case_access(current_user, doc.case_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    doc.sha256 = target_ver.sha256
    doc.storage_path = target_ver.storage_path
    if os.path.exists(target_ver.storage_path):
        doc.size_bytes = os.path.getsize(target_ver.storage_path)

    audit = AuditLog(
        id=f"audit-{uuid.uuid4().hex[:8]}",
        timestamp=datetime.datetime.utcnow(),
        user_id=current_user.id,
        action="DOCUMENT_VERSION_RESTORE",
        case_id=doc.case_id,
        resource=f"Document {doc.filename} restored to Version {target_ver.version_number}",
        result="success"
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "message": f"Document {doc.id} restored to Version {target_ver.version_number}.",
        "restoredVersion": target_ver.version_number,
        "sha256": doc.sha256
    }
