"""
COMPONENT TEST: Criminal Intelligence Reports Generation
==========================================================
Tests markdown intelligence report generation with real database content (entities, relationships, graph metrics, findings, evidence).
"""
import pytest
from app.api.reports import generate_case_report, ReportRequest
from app.models.models import User


class TestReports:
    """Phase 26 — Report generation verification."""

    def test_report_generation(self, seeded_db):
        user = User(id="u-admin", name="Admin User", role="admin")
        req = ReportRequest(case_id="case-101", format="markdown")

        res = generate_case_report(req, current_user=user, db=seeded_db)

        report_text = res.get("reportMarkdown", "")
        summary = res.get("summary", {})

        print(f"\n{'='*60}")
        print(f"REPORT GENERATION (case-101):")
        print(f"  Summary: {summary}")
        print(f"  Report Length: {len(report_text)} chars")
        print(f"  First 300 chars:")
        print("  " + "\n  ".join(report_text[:300].split("\n")))
        print(f"STATUS:   {'PASS' if len(report_text) > 200 and summary.get('entityCount', 0) > 0 else 'FAIL'}")
        print(f"{'='*60}")

        assert "NEXUS-CI INTELLIGENCE REPORT" in report_text
        assert "Operation Nightfall" in report_text
        assert summary["entityCount"] > 0
