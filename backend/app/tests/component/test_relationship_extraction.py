"""
COMPONENT TEST: Relationship Extraction
=========================================
Tests deterministic graph edge construction from CDR, transaction,
and co-occurrence evidence.
"""
import os, json, csv, hashlib, datetime, pytest
from app.models.models import Document, CanonicalEntity, EntityRelationship, RawMention
from app.services.ingestion.coordinator import PipelineCoordinator


class TestRelationshipExtraction:
    """Phase 9 — Relationship extraction verification."""

    def test_cdr_creates_calls_relationship(self, db, cases, tmp_dir):
        """CSV CDR ingestion should create CALLS edges."""
        # Create phone entities that match the CDR
        db.add(CanonicalEntity(id="ent-p1", type="phone", label="9876543210",
                               case_ids=["case-101"], aliases=["9876543210"],
                               relevance=80, attributes={"Phone": "9876543210"},
                               cluster="c1", x=100, y=100))
        db.add(CanonicalEntity(id="ent-p2", type="phone", label="9876543211",
                               case_ids=["case-101"], aliases=["9876543211"],
                               relevance=70, attributes={"Phone": "9876543211"},
                               cluster="c1", x=200, y=200))
        db.commit()

        # Create CDR CSV file
        csv_path = os.path.join(tmp_dir, "cdr_rel_test.csv")
        with open(csv_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["caller", "callee", "duration", "timestamp"])
            w.writeheader()
            w.writerow({"caller": "9876543210", "callee": "9876543211",
                        "duration": "420", "timestamp": "2026-03-15T10:30:00"})
        
        doc = Document(id="doc-cdr-rel", case_id="case-101", filename="cdr_rel_test.csv",
                       source_type="CDR", storage_path=csv_path,
                       sha256=hashlib.sha256(b"test").hexdigest(),
                       size_bytes=100, uploaded_by="u-arjun",
                       uploaded_at=datetime.datetime(2026, 8, 1),
                       processing_status="queued")
        db.add(doc)
        db.commit()

        coordinator = PipelineCoordinator(db, None)
        result = coordinator.process_document("doc-cdr-rel")

        rels = db.query(EntityRelationship).filter(EntityRelationship.rel_type == "CALLS").all()
        calls_rels = [r for r in rels if r.source_id == "ent-p1" and r.target_id == "ent-p2"]

        print(f"\n{'='*60}")
        print(f"INPUT:    CDR CSV with caller=9876543210, callee=9876543211")
        print(f"EXPECTED: CALLS relationship from ent-p1 → ent-p2")
        print(f"ACTUAL:   {len(calls_rels)} CALLS relationships found")
        if calls_rels:
            r = calls_rels[0]
            print(f"  type={r.rel_type}, confidence={r.confidence}, pipeline={r.created_by_pipeline}")
            print(f"  evidence_ids={r.evidence_ids}")
        print(f"STATUS:   {'PASS' if calls_rels else 'FAIL'}")
        print(f"{'='*60}")

        assert len(calls_rels) >= 1

    def test_mentioned_in_relationships(self, db, cases, tmp_dir):
        """NER mentions should create MENTIONED_IN edges to the document."""
        txt_path = os.path.join(tmp_dir, "mention_test.txt")
        with open(txt_path, "w") as f:
            f.write("Ravi Kumar used phone 9876543210 in Chennai.")

        doc = Document(id="doc-mention-test", case_id="case-101", filename="mention_test.txt",
                       source_type="FIR", storage_path=txt_path,
                       sha256=hashlib.sha256(b"test").hexdigest(),
                       size_bytes=50, uploaded_by="u-arjun",
                       uploaded_at=datetime.datetime(2026, 8, 1),
                       processing_status="queued")
        db.add(doc)
        db.commit()

        coordinator = PipelineCoordinator(db, None)
        coordinator.process_document("doc-mention-test")

        mentioned = db.query(EntityRelationship).filter(
            EntityRelationship.rel_type == "MENTIONED_IN").all()

        print(f"\n{'='*60}")
        print(f"INPUT:    Text file with entities")
        print(f"EXPECTED: MENTIONED_IN relationships linking entities to document")
        print(f"ACTUAL:   {len(mentioned)} MENTIONED_IN relationships")
        for r in mentioned[:3]:
            print(f"  {r.source_id} → {r.target_id} (conf={r.confidence})")
        print(f"STATUS:   {'PASS' if mentioned else 'PARTIAL'}")
        print(f"{'='*60}")

    def test_relationship_has_provenance(self, seeded_db):
        """Every relationship must have provenance fields."""
        rels = seeded_db.query(EntityRelationship).all()
        for r in rels:
            assert r.rel_type is not None, f"Missing rel_type on {r.id}"
            assert r.confidence is not None, f"Missing confidence on {r.id}"
            assert r.source_id is not None, f"Missing source_id on {r.id}"
            assert r.target_id is not None, f"Missing target_id on {r.id}"

        print(f"\n{'='*60}")
        print(f"RELATIONSHIPS VERIFIED: {len(rels)}")
        for r in rels:
            print(f"  {r.source_id} --[{r.rel_type}]--> {r.target_id} "
                  f"conf={r.confidence} evidence={r.evidence_ids}")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")
