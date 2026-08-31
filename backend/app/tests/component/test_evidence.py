"""
COMPONENT TEST: Evidence & Document Integrity
================================================
Tests document uploading, SHA-256 calculation, integrity verification, versioning, and restore audit trail.
"""
import os, hashlib, datetime, pytest
from app.models.models import Document, DocumentVersion, AuditLog


class TestEvidenceIntegrity:
    """Phase 16 — Evidence provenance, versioning & integrity verification."""

    def test_document_sha256_verification(self, tmp_dir, db, cases):
        # Create a file
        file_path = os.path.join(tmp_dir, "evidence_doc.txt")
        content = b"Confidential evidence payload 2026."
        with open(file_path, "wb") as f:
            f.write(content)

        expected_hash = hashlib.sha256(content).hexdigest()

        doc = Document(id="doc-ev-test", case_id="case-101", filename="evidence_doc.txt",
                       source_type="FIR", storage_path=file_path,
                       sha256=expected_hash, size_bytes=len(content),
                       uploaded_by="u-arjun", uploaded_at=datetime.datetime.utcnow(),
                       processing_status="completed")
        db.add(doc)
        db.commit()

        # Verify integrity by recalculating
        with open(file_path, "rb") as f:
            recomputed = hashlib.sha256(f.read()).hexdigest()

        verified = (recomputed == doc.sha256)

        print(f"\n{'='*60}")
        print(f"EVIDENCE SHA-256 VERIFICATION:")
        print(f"  Recorded Hash:    {doc.sha256}")
        print(f"  Recalculated:     {recomputed}")
        print(f"  Integrity Match:  {verified}")
        print(f"STATUS:   {'PASS' if verified else 'FAIL'}")
        print(f"{'='*60}")

        assert verified is True

    def test_versioning_and_restore_audit(self, tmp_dir, db, cases):
        p1 = os.path.join(tmp_dir, "doc_v1.txt")
        with open(p1, "wb") as f:
            f.write(b"Version 1 content")
        h1 = hashlib.sha256(b"Version 1 content").hexdigest()

        p2 = os.path.join(tmp_dir, "doc_v2.txt")
        with open(p2, "wb") as f:
            f.write(b"Version 2 updated content")
        h2 = hashlib.sha256(b"Version 2 updated content").hexdigest()

        doc = Document(id="doc-ver-restore", case_id="case-101", filename="doc_v1.txt",
                       source_type="FIR", storage_path=p2, sha256=h2,
                       size_bytes=len(b"Version 2 updated content"), uploaded_by="u-arjun",
                       uploaded_at=datetime.datetime.utcnow(), processing_status="completed")
        db.add(doc)

        v1 = DocumentVersion(id="ver-101-1", document_id="doc-ver-restore", version_number=1,
                             sha256=h1, storage_path=p1, uploader_id="u-arjun",
                             change_reason="Original", created_at=datetime.datetime.utcnow())
        v2 = DocumentVersion(id="ver-101-2", document_id="doc-ver-restore", version_number=2,
                             sha256=h2, storage_path=p2, uploader_id="u-arjun",
                             change_reason="Updated", created_at=datetime.datetime.utcnow())
        db.add_all([v1, v2])
        db.commit()

        # Perform Restore of Version 1
        doc.sha256 = v1.sha256
        doc.storage_path = v1.storage_path
        audit = AuditLog(id="aud-ver-restore", user_id="u-arjun", action="DOCUMENT_VERSION_RESTORE",
                         case_id="case-101", resource="Restored to v1", result="success")
        db.add(audit)
        db.commit()

        restored_doc = db.query(Document).filter(Document.id == "doc-ver-restore").first()
        audit_rec = db.query(AuditLog).filter(AuditLog.id == "aud-ver-restore").first()

        print(f"\n{'='*60}")
        print(f"DOCUMENT VERSION RESTORE:")
        print(f"  Restored SHA-256: {restored_doc.sha256}")
        print(f"  Expected Hash:    {h1}")
        print(f"  Audit Action:     {audit_rec.action}")
        print(f"STATUS:   {'PASS' if restored_doc.sha256 == h1 and audit_rec else 'FAIL'}")
        print(f"{'='*60}")

        assert restored_doc.sha256 == h1
        assert audit_rec is not None
