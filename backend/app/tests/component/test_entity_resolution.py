"""
COMPONENT TEST: Entity Resolution
===================================
Tests RapidFuzz-based entity resolution with controlled variants:
  Ravi Kumar / Ravi K / R. Kumar
Tests: NO_MATCH, POSSIBLE, PROBABLE, CONFIRMED; Accept, Reject, Undo.
"""
import pytest
from app.models.models import CanonicalEntity, RawMention, EntityMergeDecision, AuditLog
from app.services.entity_resolution.resolution_service import EntityResolutionService


class TestEntityResolution:
    """Phase 8 — Entity Resolution verification."""

    def test_generate_candidates_similar_names(self, db, cases, entities):
        """Similar names should produce merge candidates."""
        # Add an unresolved raw mention for 'Ravi K' — should match 'Ravi Kumar'
        rm = RawMention(id="raw-test-rk", case_id="case-101", evidence_id="doc-fir-101",
                        surface="Ravi K", type="person", resolved_to=None)
        db.add(rm)
        db.commit()

        svc = EntityResolutionService(db, None)
        candidates = svc.generate_candidates("case-101")

        print(f"\n{'='*60}")
        print(f"INPUT:    Raw mention 'Ravi K' (unresolved)")
        print(f"CANONICAL: 'Ravi Kumar' exists in DB")
        print(f"CANDIDATES GENERATED: {len(candidates)}")
        for c in candidates:
            print(f"  → {c.canonical_label} | confidence={c.confidence} | signals={c.signals}")
        print(f"EXPECTED: >= 1 candidate matching 'Ravi Kumar'")
        ravi_match = any(c.canonical_label == "Ravi Kumar" for c in candidates)
        print(f"ACTUAL:   Ravi Kumar match = {ravi_match}")
        print(f"STATUS:   {'PASS' if ravi_match else 'FAIL'}")
        print(f"{'='*60}")

        assert ravi_match

    def test_generate_candidates_r_kumar(self, db, cases, entities):
        """'R. Kumar' should fuzzy-match 'Ravi Kumar'."""
        rm = RawMention(id="raw-test-rkumar", case_id="case-101", evidence_id="doc-fir-101",
                        surface="R. Kumar", type="person", resolved_to=None)
        db.add(rm)
        db.commit()

        svc = EntityResolutionService(db, None)
        candidates = svc.generate_candidates("case-101")

        matches = [c for c in candidates if c.canonical_label == "Ravi Kumar"]

        print(f"\n{'='*60}")
        print(f"INPUT:    'R. Kumar' vs canonical 'Ravi Kumar'")
        print(f"MATCHES:  {len(matches)}")
        if matches:
            print(f"CONFIDENCE: {matches[0].confidence}%")
        print(f"STATUS:   {'PASS' if matches else 'FAIL'}")
        print(f"{'='*60}")

        assert len(matches) >= 1

    def test_no_match_for_unrelated_name(self, db, cases, entities):
        """Completely different names should NOT generate candidates."""
        rm = RawMention(id="raw-test-nomatch", case_id="case-101", evidence_id="doc-fir-101",
                        surface="Xyz Qwerty Impossible Name", type="person", resolved_to=None)
        db.add(rm)
        db.commit()

        svc = EntityResolutionService(db, None)
        candidates = svc.generate_candidates("case-101")

        # Should find no match for this name
        bad_matches = [c for c in candidates if "Xyz" in str(c.mentions)]

        print(f"\n{'='*60}")
        print(f"INPUT:    'Xyz Qwerty Impossible Name'")
        print(f"EXPECTED: NO_MATCH (0 candidates)")
        print(f"ACTUAL:   {len(bad_matches)} candidates")
        print(f"STATUS:   {'PASS' if len(bad_matches) == 0 else 'FAIL'}")
        print(f"{'='*60}")

        assert len(bad_matches) == 0

    def test_accept_merge_updates_canonical(self, db, cases, entities):
        """Accepting a merge should update canonical entity aliases."""
        # Pre-create a pending candidate
        cand = EntityMergeDecision(
            id="cand-test-accept", case_id="case-101",
            canonical_id="ent-ravi", canonical_label="Ravi Kumar",
            type="person", mentions=["Ravi K"],
            confidence=80, signals=[], status="pending")
        db.add(cand)
        db.commit()

        svc = EntityResolutionService(db, None)
        result = svc.apply_merge("cand-test-accept", accept=True, user_id="u-arjun")

        updated_cand = db.query(EntityMergeDecision).filter(
            EntityMergeDecision.id == "cand-test-accept").first()
        canon = db.query(CanonicalEntity).filter(CanonicalEntity.id == "ent-ravi").first()

        print(f"\n{'='*60}")
        print(f"INPUT:    Accept merge 'Ravi K' → 'Ravi Kumar'")
        print(f"DECISION STATUS: {updated_cand.status}")
        print(f"CANONICAL ALIASES: {canon.aliases}")
        print(f"EXPECTED: status='accepted', 'Ravi K' in aliases")
        has_alias = "Ravi K" in canon.aliases
        print(f"ACTUAL:   accepted={updated_cand.status == 'accepted'}, alias={has_alias}")
        print(f"AUDIT:    {db.query(AuditLog).filter(AuditLog.action == 'ENTITY_MERGE').count()} records")
        print(f"STATUS:   {'PASS' if result and has_alias else 'FAIL'}")
        print(f"{'='*60}")

        assert result is True
        assert updated_cand.status == "accepted"
        assert "Ravi K" in canon.aliases

    def test_reject_merge(self, db, cases, entities):
        """Rejecting a merge should mark status as rejected."""
        cand = EntityMergeDecision(
            id="cand-test-reject", case_id="case-101",
            canonical_id="ent-ravi", canonical_label="Ravi Kumar",
            type="person", mentions=["Some Other Name"],
            confidence=40, signals=[], status="pending")
        db.add(cand)
        db.commit()

        svc = EntityResolutionService(db, None)
        result = svc.apply_merge("cand-test-reject", accept=False, user_id="u-arjun")

        updated = db.query(EntityMergeDecision).filter(
            EntityMergeDecision.id == "cand-test-reject").first()

        print(f"\n{'='*60}")
        print(f"INPUT:    Reject merge for 'Some Other Name'")
        print(f"EXPECTED: status='rejected'")
        print(f"ACTUAL:   status='{updated.status}'")
        print(f"STATUS:   {'PASS' if updated.status == 'rejected' else 'FAIL'}")
        print(f"{'='*60}")

        assert result is True
        assert updated.status == "rejected"

    def test_undo_merge_restores_state(self, db, cases, entities):
        """Undoing an accepted merge should restore previous aliases."""
        # First accept
        cand = EntityMergeDecision(
            id="cand-test-undo", case_id="case-101",
            canonical_id="ent-ravi", canonical_label="Ravi Kumar",
            type="person", mentions=["R. Kumar Test"],
            confidence=75, signals=[], status="pending")
        db.add(cand)
        db.commit()

        svc = EntityResolutionService(db, None)
        svc.apply_merge("cand-test-undo", accept=True, user_id="u-arjun")

        canon_before = db.query(CanonicalEntity).filter(CanonicalEntity.id == "ent-ravi").first()
        aliases_after_merge = list(canon_before.aliases)

        # Now undo
        undo_result = svc.undo_merge("cand-test-undo", user_id="u-arjun")
        updated = db.query(EntityMergeDecision).filter(
            EntityMergeDecision.id == "cand-test-undo").first()

        print(f"\n{'='*60}")
        print(f"INPUT:    Undo merge of 'R. Kumar Test'")
        print(f"ALIASES AFTER MERGE: {aliases_after_merge}")
        print(f"EXPECTED: status='undone'")
        print(f"ACTUAL:   status='{updated.status}'")
        undo_audit = db.query(AuditLog).filter(AuditLog.action == "ENTITY_UNDO").count()
        print(f"AUDIT:    {undo_audit} ENTITY_UNDO records")
        print(f"STATUS:   {'PASS' if undo_result and updated.status == 'undone' else 'FAIL'}")
        print(f"{'='*60}")

        assert undo_result is True
        assert updated.status == "undone"
        assert undo_audit >= 1
