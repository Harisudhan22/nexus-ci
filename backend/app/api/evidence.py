import os
import uuid
import datetime
import hashlib
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from fastapi.responses import Response, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.db.postgres import get_db
from app.db.neo4j_db import get_neo4j
from app.core.dependencies import get_current_user, verify_case_access
from app.models.models import Document, User, RawMention, Case, AuditLog, DocumentVersion
from app.services.ingestion.coordinator import PipelineCoordinator
from app.schemas.evidence import EvidenceResponse, IntegrityVerificationResponse
from app.services.evidence.storage_backend import (
    get_storage_backend,
    get_storage_status,
    calculate_sha256,
    make_storage_key,
)

router = APIRouter(tags=["evidence"])

ALLOWED_EXTENSIONS = {"pdf", "docx", "csv", "json", "png", "jpg", "jpeg", "txt", "log", "wav", "mp3", "m4a"}
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB


def validate_file(filename: str, size: int):
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension: '{ext}'. Allowed: {ALLOWED_EXTENSIONS}"
        )
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of 15MB (got {size / (1024 * 1024):.1f}MB)"
        )


@router.get("/evidence/storage/status")
def get_evidence_storage_status(current_user: User = Depends(get_current_user)):
    """Returns status of the active object storage backend (Local vs S3)."""
    return get_storage_status()


@router.post("/cases/{case_id}/documents", response_model=EvidenceResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_document(
    case_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_type: str = Form("JSON"),
    title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    neo4j_sess = Depends(get_neo4j)
):
    if not verify_case_access(current_user, case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this case.")

    db_case = db.query(Case).filter(Case.id == case_id).first()
    if not db_case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    contents = file.file.read()
    file_size = len(contents)
    file.file.seek(0)

    validate_file(file.filename, file_size)

    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    storage_key = make_storage_key(case_id, doc_id, file.filename, version=1)

    storage = get_storage_backend()
    storage_location = storage.save(storage_key, contents, content_type=file.content_type or "application/octet-stream")
    sha256 = calculate_sha256(contents)

    doc = Document(
        id=doc_id,
        case_id=case_id,
        filename=file.filename,
        source_type=source_type,
        storage_path=storage_key,   # Store canonical storage key in PostgreSQL
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
        resource=f"Document {file.filename} (storage={storage.backend_name})",
        result="success"
    )
    db.add(audit)
    db.commit()

    try:
        from app.services.ingestion.task_queue import create_task
        task_id = create_task("document_processing", {"document_id": doc_id, "case_id": case_id})
        queue_status = "queued"
    except Exception:
        background_tasks.add_task(_run_pipeline, doc_id)
        task_id = None
        queue_status = "processing"

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
        "status": queue_status,
        "relevance": 50,
        "entityMentions": [],
        **({"taskId": task_id} if task_id else {})
    }


def _run_pipeline(doc_id: str):
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

    mentions = db.query(RawMention).filter(RawMention.evidence_id == id).all()
    mention_ids = list(set([m.resolved_to for m in mentions if m.resolved_to]))
    status_mapped = "processed" if doc.processing_status == "completed" else ("failed" if doc.processing_status == "failed" else "processing")

    return {
        "id": doc.id,
        "caseId": doc.case_id,
        "title": doc.filename,
        "sourceType": doc.source_type,
        "fileName": doc.filename,
        "sha256": doc.sha256,
        "uploadedAt": doc.uploaded_at.isoformat() if doc.uploaded_at else "",
        "uploadedBy": doc.uploaded_by,
        "sizeBytes": doc.size_bytes,
        "status": status_mapped,
        "relevance": 75 if doc.processing_status == "completed" else 0,
        "extractedText": doc.extracted_text,
        "rows": doc.rows_data,
        "entityMentions": mention_ids
    }


@router.get("/documents/{id}/signed-url")
def get_document_signed_url(
    id: str,
    expires: int = 3600,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generates a short-lived download URL for evidence documents."""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not verify_case_access(current_user, doc.case_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    storage = get_storage_backend()
    signed_url = storage.generate_signed_url(doc.storage_path, expires_in=expires)

    return {
        "documentId": doc.id,
        "filename": doc.filename,
        "signedUrl": signed_url,
        "expiresInSeconds": expires,
        "storageBackend": storage.backend_name.upper(),
    }


@router.get("/documents/{id}/download")
def download_document(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Downloads evidence document binary content through storage abstraction."""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not verify_case_access(current_user, doc.case_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    storage = get_storage_backend()
    file_bytes = storage.load(doc.storage_path)

    # Fallback to local filesystem if load by key fails (legacy data compatibility)
    if file_bytes is None and os.path.exists(doc.storage_path):
        with open(doc.storage_path, "rb") as f:
            file_bytes = f.read()

    if file_bytes is None:
        raise HTTPException(status_code=404, detail="Document content missing from storage backend.")

    media_type = "application/pdf" if doc.filename.endswith(".pdf") else "application/octet-stream"
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'}
    )


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

    storage = get_storage_backend()
    file_bytes = storage.load(doc.storage_path)

    # Legacy filesystem fallback check
    if file_bytes is None and os.path.exists(doc.storage_path):
        with open(doc.storage_path, "rb") as f:
            file_bytes = f.read()

    if file_bytes is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file missing from storage backend.")

    recalculated = calculate_sha256(file_bytes)
    verified = (recalculated == doc.sha256)

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
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not verify_case_access(current_user, doc.case_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    contents = file.file.read()
    validate_file(file.filename, len(contents))
    sha256 = calculate_sha256(contents)

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
    version_key = make_storage_key(doc.case_id, id, file.filename, version=new_version_num)

    storage = get_storage_backend()
    storage.save(version_key, contents, content_type=file.content_type or "application/octet-stream")

    ver_obj = DocumentVersion(
        id=f"ver-{uuid.uuid4().hex[:8]}",
        document_id=id,
        version_number=new_version_num,
        sha256=sha256,
        storage_path=version_key,
        uploader_id=current_user.id,
        change_reason=change_reason,
        created_at=datetime.datetime.utcnow()
    )
    db.add(ver_obj)

    doc.sha256 = sha256
    doc.storage_path = version_key
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
    doc = db.query(Document).filter(Document.id == id).first()
    target_ver = db.query(DocumentVersion).filter(DocumentVersion.id == version_id, DocumentVersion.document_id == id).first()
    if not doc or not target_ver:
        raise HTTPException(status_code=404, detail="Document or Version not found.")
    if not verify_case_access(current_user, doc.case_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    doc.sha256 = target_ver.sha256
    doc.storage_path = target_ver.storage_path

    storage = get_storage_backend()
    file_bytes = storage.load(target_ver.storage_path)
    if file_bytes is not None:
        doc.size_bytes = len(file_bytes)
    elif os.path.exists(target_ver.storage_path):
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
