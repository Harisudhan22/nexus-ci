"""
COMPONENT TEST: NER — Named Entity Recognition
================================================
Tests the EntityExtractor (spaCy + regex) against controlled text
with KNOWN expected entities.

Phases 7: PERSON, LOCATION, VEHICLE, PHONE, ACCOUNT, CASE extraction.
"""
import pytest
from app.services.nlp.ner_service import EntityExtractor


class TestNER:
    """Phase 7 — NER verification with deterministic inputs."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.extractor = EntityExtractor()

    def test_phone_extraction(self):
        """Extract phone numbers via regex."""
        text = "Ravi Kumar used phone 9876543210 and also 9123456789."
        mentions = self.extractor.extract(text, "case-101", "doc-001")

        phones = [m for m in mentions if m["type"] == "phone"]
        phone_surfaces = [p["surface"] for p in phones]

        print(f"\n{'='*60}")
        print(f"INPUT:    {text}")
        print(f"EXPECTED: PHONE: 9876543210, 9123456789")
        print(f"ACTUAL:   {phone_surfaces}")
        print(f"STATUS:   {'PASS' if '9876543210' in phone_surfaces else 'FAIL'}")
        print(f"{'='*60}")

        assert "9876543210" in phone_surfaces

    def test_vehicle_extraction(self):
        """Extract Indian vehicle registration plates via regex."""
        text = "Vehicle TN38AB1234 was spotted near Adyar. Also DL01CA5678."
        mentions = self.extractor.extract(text, "case-101", "doc-001")

        vehicles = [m for m in mentions if m["type"] == "vehicle"]
        veh_surfaces = [v["surface"] for v in vehicles]

        print(f"\n{'='*60}")
        print(f"INPUT:    {text}")
        print(f"EXPECTED: VEHICLE: TN38AB1234, DL01CA5678")
        print(f"ACTUAL:   {veh_surfaces}")
        print(f"STATUS:   {'PASS' if 'TN38AB1234' in veh_surfaces else 'FAIL'}")
        print(f"{'='*60}")

        assert "TN38AB1234" in veh_surfaces

    def test_account_extraction(self):
        """Extract account identifiers via regex."""
        text = "Suspicious transfer to Account A101 from A201."
        mentions = self.extractor.extract(text, "case-205", "doc-002")

        accounts = [m for m in mentions if m["type"] == "account"]
        acc_surfaces = [a["surface"] for a in accounts]

        print(f"\n{'='*60}")
        print(f"INPUT:    {text}")
        print(f"EXPECTED: ACCOUNT: A101, A201")
        print(f"ACTUAL:   {acc_surfaces}")
        print(f"STATUS:   {'PASS' if any('A101' in s for s in acc_surfaces) else 'FAIL'}")
        print(f"{'='*60}")

        assert any("A101" in s for s in acc_surfaces)

    def test_person_extraction_spacy_or_fallback(self):
        """Extract person names via spaCy NER or capitalized word fallback."""
        text = "Ravi Kumar met Suresh near Chennai Central using vehicle TN38AB1234."
        mentions = self.extractor.extract(text, "case-101", "doc-003")

        persons = [m for m in mentions if m["type"] == "person"]
        person_names = [p["surface"] for p in persons]

        print(f"\n{'='*60}")
        print(f"INPUT:    {text}")
        print(f"EXPECTED: PERSON: Ravi Kumar, Suresh")
        print(f"ACTUAL:   {person_names}")
        print(f"ENGINE:   {'spaCy' if self.extractor.nlp else 'regex fallback'}")

        has_ravi = any("Ravi" in n for n in person_names)
        print(f"STATUS:   {'PASS' if has_ravi else 'PARTIAL'}")
        print(f"{'='*60}")

        # At minimum, regex fallback should capture capitalized names
        assert len(persons) >= 1

    def test_location_extraction(self):
        """Extract location entities (requires spaCy GPE/LOC labels)."""
        text = "The suspect was last seen in Chennai Central near the railway station."
        mentions = self.extractor.extract(text, "case-101", "doc-004")

        locations = [m for m in mentions if m["type"] == "location"]
        loc_names = [l["surface"] for l in locations]

        print(f"\n{'='*60}")
        print(f"INPUT:    {text}")
        print(f"EXPECTED: LOCATION: Chennai Central (if spaCy available)")
        print(f"ACTUAL:   {loc_names}")
        print(f"ENGINE:   {'spaCy' if self.extractor.nlp else 'regex fallback'}")
        print(f"STATUS:   {'PASS' if locations else 'PARTIAL (no spaCy)'}")
        print(f"{'='*60}")

        # Location extraction depends on spaCy model
        if self.extractor.nlp:
            assert len(locations) >= 1

    def test_case_id_extraction(self):
        """Extract case ID references via regex."""
        text = "This relates to CASE-101 and CASE-205."
        mentions = self.extractor.extract(text, "case-101", "doc-005")

        cases = [m for m in mentions if m["type"] == "case"]
        case_ids = [c["surface"] for c in cases]

        print(f"\n{'='*60}")
        print(f"INPUT:    {text}")
        print(f"EXPECTED: CASE: CASE-101, CASE-205")
        print(f"ACTUAL:   {case_ids}")
        print(f"STATUS:   {'PASS' if 'CASE-101' in case_ids else 'FAIL'}")
        print(f"{'='*60}")

        assert "CASE-101" in case_ids
        assert "CASE-205" in case_ids

    def test_deduplication(self):
        """Ensure duplicate mentions of same entity are deduplicated."""
        text = "Ravi Kumar called 9876543210. Then 9876543210 was called again."
        mentions = self.extractor.extract(text, "case-101", "doc-006")

        phones = [m for m in mentions if m["type"] == "phone"]

        print(f"\n{'='*60}")
        print(f"INPUT:    {text}")
        print(f"EXPECTED: 1 unique phone mention (deduplicated)")
        print(f"ACTUAL:   {len(phones)} phone mentions")
        print(f"STATUS:   {'PASS' if len(phones) == 1 else 'FAIL'}")
        print(f"{'='*60}")

        assert len(phones) == 1

    def test_combined_fir_text(self):
        """Full FIR text with mixed entity types."""
        from .conftest import FIR_TEXT
        mentions = self.extractor.extract(FIR_TEXT, "case-101", "doc-fir-101")

        type_counts = {}
        for m in mentions:
            type_counts[m["type"]] = type_counts.get(m["type"], 0) + 1

        print(f"\n{'='*60}")
        print(f"INPUT:    FIR-101 text ({len(FIR_TEXT)} chars)")
        print(f"TOTAL MENTIONS: {len(mentions)}")
        for t, c in sorted(type_counts.items()):
            print(f"  {t.upper()}: {c}")
        print(f"EXPECTED: phone>=1, vehicle>=1")
        print(f"STATUS:   {'PASS' if type_counts.get('phone', 0) >= 1 else 'FAIL'}")
        print(f"{'='*60}")

        assert type_counts.get("phone", 0) >= 1
        assert type_counts.get("vehicle", 0) >= 1

    def test_empty_text_returns_empty(self):
        """Empty text should return no mentions."""
        mentions = self.extractor.extract("", "case-101", "doc-007")
        assert mentions == []

        mentions = self.extractor.extract(None, "case-101", "doc-008")
        assert mentions == []
