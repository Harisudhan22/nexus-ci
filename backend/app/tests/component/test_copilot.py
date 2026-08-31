"""
COMPONENT TEST: AI Copilot & Natural Language Graph Query
===========================================================
Tests multi-source grounded copilot solvers, payload fields, and Cypher injection rejection.
"""
import pytest
from app.services.copilot.copilot_service import CopilotService


class TestCopilot:
    """Phase 22 & Phase 23 — AI Copilot & Natural Language Graph Query Rejection."""

    def test_copilot_cross_case_query(self, seeded_db):
        svc = CopilotService(seeded_db, None)
        res = svc.query("case-101", "Which previous cases are connected to Ravi Kumar?", "u-admin")

        print(f"\n{'='*60}")
        print(f"COPILOT CROSS-CASE QUERY:")
        print(f"  Answer:        {res.get('answer')}")
        print(f"  Sources:       {res.get('sources')}")
        print(f"  Cases:         {res.get('cases')}")
        print(f"  Entities:      {res.get('entities')}")
        print(f"  ProviderType:  {res.get('providerType')}")
        print(f"STATUS:   {'PASS' if len(res.get('cases', [])) >= 2 else 'FAIL'}")
        print(f"{'='*60}")

        assert len(res.get("cases", [])) >= 2
        assert "ent-ravi" in res.get("entities", [])

    def test_copilot_structured_response_fields(self, seeded_db):
        svc = CopilotService(seeded_db, None)
        res = svc.query("case-101", "Summarize case-101", "u-admin")

        required_fields = ["answer", "summary", "confidence", "providerType",
                           "sources", "cases", "entities", "key_reasons", "analytical_interpretation"]

        print(f"\n{'='*60}")
        print(f"COPILOT RESPONSE SCHEMA CHECK:")
        for f in required_fields:
            print(f"  {f:25s}: {'PRESENT' if f in res else 'MISSING'}")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

        for f in required_fields:
            assert f in res, f"Field {f} missing from Copilot response schema"

    def test_malicious_cypher_injection_rejection(self, seeded_db):
        """Natural language graph query endpoint must reject malicious Cypher queries."""
        from app.api.ai import sanitize_cypher_input

        malicious_input = "MATCH (n) DETACH DELETE n"
        is_safe = sanitize_cypher_input(malicious_input)

        print(f"\n{'='*60}")
        print(f"CYPHER INJECTION REJECTION TEST:")
        print(f"  Input:   \"{malicious_input}\"")
        print(f"  Sanitized Safe: {is_safe}")
        print(f"STATUS:   {'PASS' if not is_safe else 'FAIL'}")
        print(f"{'='*60}")

        assert is_safe is False
