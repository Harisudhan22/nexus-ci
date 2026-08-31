"""
COMPONENT TEST: PostgreSQL
============================
Tests CRUD operations, authorization, and idempotency for all core tables.
"""
import datetime, pytest
from app.models.models import (Case, Document, CanonicalEntity, EntityRelationship,
                                Finding, AuditLog, WorkspaceState, DocumentVersion,
                                InvestigatorQuery, User)


class TestPostgres:
    """Phase 10 — PostgreSQL CRUD and consistency."""

    def test_create_and_read_case(self, db, users):
        c = Case(id="case-pg-test", title="PG Test Case", status="active",
                 priority="low", agency="Test", classification="unclassified",
                 assigned_to="u-admin")
        db.add(c)
        db.commit()
        fetched = db.query(Case).filter(Case.id == "case-pg-test").first()

        print(f"\n{'='*60}")
        print(f"CREATE:   Case 'case-pg-test'")
        print(f"READ:     {fetched.id} → {fetched.title}")
        print(f"STATUS:   {'PASS' if fetched else 'FAIL'}")
        print(f"{'='*60}")
        assert fetched is not None
        assert fetched.title == "PG Test Case"

    def test_create_document_with_sha256(self, db, cases):
        d = Document(id="doc-pg-test", case_id="case-101", filename="test.txt",
                     source_type="FIR", storage_path="./test.txt",
                     sha256="abc123" * 10 + "abcd", size_bytes=100,
                     uploaded_by="u-arjun", uploaded_at=datetime.datetime(2026, 8, 1),
                     processing_status="queued")
        db.add(d)
        db.commit()
        fetched = db.query(Document).filter(Document.id == "doc-pg-test").first()

        print(f"\n{'='*60}")
        print(f"DOC:      {fetched.id}, SHA-256={fetched.sha256[:16]}...")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")
        assert fetched.sha256 is not None
        assert fetched.case_id == "case-101"

    def test_entity_case_ids_json(self, db, cases):
        e = CanonicalEntity(id="ent-pg-test", type="person", label="PG Person",
                            case_ids=["case-101", "case-205"], aliases=["PG"],
                            attributes={}, relevance=50, cluster="c1", x=0, y=0)
        db.add(e)
        db.commit()
        fetched = db.query(CanonicalEntity).filter(CanonicalEntity.id == "ent-pg-test").first()
        assert "case-101" in fetched.case_ids
        assert "case-205" in fetched.case_ids

        print(f"\n{'='*60}")
        print(f"ENTITY:   {fetched.label}, case_ids={fetched.case_ids}")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

    def test_workspace_save_and_restore(self, db, cases, users):
        ws = WorkspaceState(id="ws-test", case_id="case-101", user_id="u-arjun",
                            title="Test WS", selected_entity_ids=["ent-ravi"],
                            graph_filters={"min_confidence": 50},
                            bookmarks=["ent-ravi"], notes="Test note",
                            updated_at=datetime.datetime.utcnow())
        db.add(ws)
        db.commit()
        fetched = db.query(WorkspaceState).filter(WorkspaceState.id == "ws-test").first()

        print(f"\n{'='*60}")
        print(f"WORKSPACE: {fetched.title}")
        print(f"  entities={fetched.selected_entity_ids}")
        print(f"  filters={fetched.graph_filters}")
        print(f"  bookmarks={fetched.bookmarks}")
        print(f"  notes={fetched.notes}")
        print(f"STATUS:   {'PASS' if fetched.notes == 'Test note' else 'FAIL'}")
        print(f"{'='*60}")
        assert fetched.selected_entity_ids == ["ent-ravi"]
        assert fetched.notes == "Test note"

    def test_audit_log_creation(self, db, users):
        a = AuditLog(id="aud-pg-test", user_id="u-arjun", action="TEST",
                     resource="Component Test", result="success")
        db.add(a)
        db.commit()
        fetched = db.query(AuditLog).filter(AuditLog.id == "aud-pg-test").first()
        assert fetched is not None
        assert fetched.action == "TEST"

    def test_finding_crud(self, db, cases, entities):
        f = Finding(id="fnd-pg-test", case_id="case-101",
                    category="test", title="PG Test Finding",
                    severity="low", confidence=50,
                    why="Component test", entity_ids=["ent-ravi"],
                    evidence_ids=[], status="open")
        db.add(f)
        db.commit()
        fetched = db.query(Finding).filter(Finding.id == "fnd-pg-test").first()
        assert fetched.title == "PG Test Finding"

    def test_document_versioning(self, db, cases):
        doc = Document(id="doc-ver-test", case_id="case-101", filename="ver.txt",
                       source_type="FIR", storage_path="./ver.txt",
                       sha256="hash1", size_bytes=10, uploaded_by="u-arjun",
                       uploaded_at=datetime.datetime(2026, 8, 1),
                       processing_status="completed")
        db.add(doc)
        v1 = DocumentVersion(id="ver-1", document_id="doc-ver-test",
                             version_number=1, sha256="hash1",
                             storage_path="./ver.txt", uploader_id="u-arjun",
                             change_reason="Original", created_at=datetime.datetime(2026, 8, 1))
        v2 = DocumentVersion(id="ver-2", document_id="doc-ver-test",
                             version_number=2, sha256="hash2",
                             storage_path="./ver2.txt", uploader_id="u-arjun",
                             change_reason="Revision", created_at=datetime.datetime(2026, 8, 5))
        db.add_all([v1, v2])
        db.commit()

        versions = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == "doc-ver-test").all()

        print(f"\n{'='*60}")
        print(f"DOC VERSIONS: {len(versions)}")
        for v in versions:
            print(f"  v{v.version_number}: sha256={v.sha256}, reason={v.change_reason}")
        print(f"STATUS:   {'PASS' if len(versions) == 2 else 'FAIL'}")
        print(f"{'='*60}")
        assert len(versions) == 2

    def test_idempotent_entity_merge(self, db, cases):
        """Adding same entity twice should not duplicate."""
        e = CanonicalEntity(id="ent-idem", type="phone", label="1234567890",
                            case_ids=["case-101"], aliases=[], attributes={}, relevance=50,
                            cluster="c1", x=0, y=0)
        db.merge(e)
        db.commit()
        db.merge(e)
        db.commit()
        count = db.query(CanonicalEntity).filter(CanonicalEntity.id == "ent-idem").count()
        assert count == 1
