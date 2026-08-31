"""
COMPONENT TEST: Role-Based Access Control (RBAC) & Clearance Enforcement
===========================================================================
Tests RBAC permission boundaries for admin, investigator (arjun), and senior_investigator (lena).
"""
import pytest
from app.core.dependencies import verify_case_access, get_accessible_case_ids
from app.models.models import User


class TestRBAC:
    """RBAC & Case clearance permission boundary verification."""

    def test_admin_access_all_cases(self, seeded_db):
        admin = User(id="u-admin", role="admin")
        assert verify_case_access(admin, "case-101", seeded_db) is True
        assert verify_case_access(admin, "case-205", seeded_db) is True
        assert get_accessible_case_ids(admin, seeded_db) is None  # None = unrestricted

    def test_investigator_case_clearance(self, seeded_db):
        arjun = User(id="u-arjun", role="investigator")
        lena = User(id="u-lena", role="investigator")

        # Arjun is assigned to case-101, Lena assigned to case-101 and case-205
        arjun_access_101 = verify_case_access(arjun, "case-101", seeded_db)
        arjun_access_205 = verify_case_access(arjun, "case-205", seeded_db)
        lena_access_205 = verify_case_access(lena, "case-205", seeded_db)

        print(f"\n{'='*60}")
        print(f"RBAC CLEARANCE VERIFICATION:")
        print(f"  Arjun → case-101: {arjun_access_101}")
        print(f"  Arjun → case-205: {arjun_access_205} (Expected: False)")
        print(f"  Lena  → case-205: {lena_access_205} (Expected: True)")
        print(f"STATUS:   {'PASS' if arjun_access_101 and not arjun_access_205 and lena_access_205 else 'FAIL'}")
        print(f"{'='*60}")

        assert arjun_access_101 is True
        assert arjun_access_205 is False
        assert lena_access_205 is True
