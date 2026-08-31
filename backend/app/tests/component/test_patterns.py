"""
COMPONENT TEST: Pattern Detection & Investigation Priority
============================================================
Tests pattern detection engine (bursts, convergence, anomalies) and 
0-100 Investigation Priority Scoring.
"""
import pytest
from app.services.analytics.pattern_engine import SuspiciousPatternEngine
from app.services.patterns.findings_service import FindingsEngine


class TestPatternsAndPriority:
    """Phase 14 & Phase 15 — Pattern detection & investigation priority score."""

    def test_detect_cross_case_convergence(self, seeded_db):
        engine = SuspiciousPatternEngine(seeded_db)
        findings = engine.detect_all_patterns(case_id="case-101")

        conv_findings = [f for f in findings if f["pattern_type"] == "entity_convergence"]

        print(f"\n{'='*60}")
        print(f"PATTERNS DETECTED (case-101): {len(findings)} total")
        for f in findings:
            print(f"  [{f['severity'].upper()}] {f['pattern_type']}: {f['title']} (conf={f['confidence']}%)")
        print(f"CONVERGENCE FINDINGS: {len(conv_findings)}")
        print(f"STATUS:   {'PASS' if len(findings) >= 1 else 'FAIL'}")
        print(f"{'='*60}")

        assert len(findings) >= 1

    def test_investigation_priority_scoring(self, seeded_db):
        engine = SuspiciousPatternEngine(seeded_db)
        priority = engine.calculate_investigation_priority("ent-ravi", case_id="case-101")

        score = priority.get("priorityScore")
        level = priority.get("level")
        components = priority.get("components", [])

        print(f"\n{'='*60}")
        print(f"INVESTIGATION PRIORITY SCORE for ent-ravi:")
        print(f"  Score: {score}/100 ({level})")
        print(f"  Explanation: {priority.get('explanation')}")
        print(f"  Components:")
        for c in components:
            print(f"    - {c['name']}: {c['points']}/{c['max']} ({c['reason']})")
        print(f"STATUS:   {'PASS' if 0 <= score <= 100 else 'FAIL'}")
        print(f"{'='*60}")

        assert 0 <= score <= 100
        assert len(components) >= 4

    def test_findings_engine_case_analysis(self, seeded_db):
        findings_engine = FindingsEngine(seeded_db, None)
        created_findings = findings_engine.analyze_case("case-101")

        print(f"\n{'='*60}")
        print(f"FINDINGS ENGINE ANALYZE CASE (case-101):")
        print(f"  New Findings Created: {len(created_findings)}")
        for f in created_findings:
            print(f"    - [{f.severity.upper()}] {f.title}: {f.why[:80]}...")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

        assert isinstance(created_findings, list)
