"""
NEXUS-CI Component Test Harness — Shared Fixtures
==================================================
Provides an in-memory SQLite database session, pre-seeded with controlled
synthetic data whose expected outputs are KNOWN and DETERMINISTIC.

Every fixture uses SYNTHETIC data only — no real personal/criminal data.
"""
import os, sys, uuid, datetime, hashlib, tempfile, json, csv
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ── ensure project root is importable ──
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from app.models.models import Base, User, Case, Document, CanonicalEntity, \
    EntityRelationship, Finding, RawMention, EntityMergeDecision, AuditLog, \
    DocumentChunk, WorkspaceState, InvestigatorQuery, DocumentVersion, SourceRecord


# ---------------------------------------------------------------------------
#  In-memory database factory
# ---------------------------------------------------------------------------
@pytest.fixture()
def db():
    """Creates an isolated in-memory SQLite session for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ---------------------------------------------------------------------------
#  Users — three roles for RBAC testing
# ---------------------------------------------------------------------------
USERS = {
    "admin": User(id="u-admin", name="Admin User", username="admin", email="admin@nexus.gov.in",
                  password_hash="$2b$12$dummy", role="admin"),
    "arjun": User(id="u-arjun", name="Arjun Mehta", username="arjun", email="arjun@nexus.gov.in",
                  password_hash="$2b$12$dummy", role="investigator"),
    "lena": User(id="u-lena", name="Lena Sharma", username="lena", email="lena@nexus.gov.in",
                 password_hash="$2b$12$dummy", role="senior_investigator"),
}

@pytest.fixture()
def users(db):
    for u in USERS.values():
        db.merge(u)
    db.commit()
    return USERS


# ---------------------------------------------------------------------------
#  Cases
# ---------------------------------------------------------------------------
CASES = [
    Case(id="case-101", title="Operation Nightfall", status="active", priority="high",
         agency="NIA", classification="secret", description="Multi-district narcotics investigation.",
         police_station="Central PS", district="Chennai City", state="Tamil Nadu",
         assigned_to="u-arjun"),
    Case(id="case-205", title="Operation Silverline", status="active", priority="medium",
         agency="CBI", classification="confidential", description="Financial fraud network.",
         police_station="Annanagar PS", district="Chennai City", state="Tamil Nadu",
         assigned_to="u-lena"),
]

@pytest.fixture()
def cases(db, users):
    for c in CASES:
        db.merge(c)
    db.commit()
    return CASES


# ---------------------------------------------------------------------------
#  Canonical Entities — KNOWN expected outputs for NER / resolution tests
# ---------------------------------------------------------------------------
ENTITIES = [
    CanonicalEntity(id="ent-ravi", type="person", label="Ravi Kumar",
                    subtitle="Primary Target", case_ids=["case-101", "case-205"],
                    aliases=["Ravi Kumar", "R. Kumar"], relevance=90,
                    attributes={"Phone": "9876543210", "Location": "Chennai Central"},
                    cluster="cluster_1", x=200.0, y=150.0),
    CanonicalEntity(id="ent-suresh", type="person", label="Suresh",
                    subtitle="Associate", case_ids=["case-101"],
                    aliases=["Suresh"], relevance=70,
                    attributes={"Location": "T Nagar"}, cluster="cluster_1",
                    x=350.0, y=200.0),
    CanonicalEntity(id="ent-arun", type="person", label="Arun",
                    subtitle="Associate", case_ids=["case-205"],
                    aliases=["Arun"], relevance=60,
                    attributes={"Location": "Adyar"}, cluster="cluster_2",
                    x=500.0, y=250.0),
    CanonicalEntity(id="ent-phone101", type="phone", label="9876543210",
                    subtitle="Phone-101", case_ids=["case-101", "case-205"],
                    aliases=["9876543210", "Phone-101"], relevance=80,
                    attributes={"Phone": "9876543210"}, cluster="cluster_1",
                    x=250.0, y=300.0),
    CanonicalEntity(id="ent-veh01", type="vehicle", label="TN38AB1234",
                    subtitle="Vehicle-V01", case_ids=["case-101"],
                    aliases=["TN38AB1234", "Vehicle-V01"], relevance=75,
                    attributes={"Plate": "TN38AB1234"}, cluster="cluster_1",
                    x=150.0, y=350.0),
    CanonicalEntity(id="ent-acc-a101", type="account", label="A101",
                    subtitle="Account-A101", case_ids=["case-205"],
                    aliases=["A101", "Account-A101"], relevance=65,
                    attributes={"Bank": "SBI"}, cluster="cluster_2",
                    x=450.0, y=350.0),
    CanonicalEntity(id="ent-loc-chennai", type="location", label="Chennai Central",
                    subtitle="Location-L03", case_ids=["case-101"],
                    aliases=["Chennai Central"], relevance=50,
                    attributes={"Location": "Chennai Central"}, cluster="cluster_1",
                    x=300.0, y=400.0),
]

@pytest.fixture()
def entities(db, cases):
    for e in ENTITIES:
        db.merge(e)
    db.commit()
    return ENTITIES


# ---------------------------------------------------------------------------
#  Relationships — KNOWN expected graph edges
# ---------------------------------------------------------------------------
RELATIONSHIPS = [
    EntityRelationship(
        id="rel-ravi-phone", source_id="ent-ravi", source_type="person",
        target_id="ent-phone101", target_type="phone", rel_type="USES",
        case_ids=["case-101", "case-205"], confidence=95, occurrences=25,
        evidence_ids=["doc-fir-101"], source="FIR-101",
        timestamp="2026-01-15", time_from="2026-01-01", time_to="2026-03-01",
        rationale="Phone registered to Ravi Kumar.", suspicious=False,
        created_by_pipeline="Seed"),
    EntityRelationship(
        id="rel-ravi-veh", source_id="ent-ravi", source_type="person",
        target_id="ent-veh01", target_type="vehicle", rel_type="OPERATES",
        case_ids=["case-101"], confidence=90, occurrences=10,
        evidence_ids=["doc-fir-101"], source="FIR-101",
        timestamp="2026-02-10", time_from="2026-02-01", time_to="2026-04-01",
        rationale="Vehicle registration linked to Ravi.", suspicious=False,
        created_by_pipeline="Seed"),
    EntityRelationship(
        id="rel-ravi-suresh", source_id="ent-ravi", source_type="person",
        target_id="ent-suresh", target_type="person", rel_type="CALLS",
        case_ids=["case-101"], confidence=85, occurrences=30,
        evidence_ids=["doc-cdr-101"], source="CDR-101",
        timestamp="2026-03-01", time_from="2026-03-01", time_to="2026-06-01",
        rationale="30 call records between Ravi and Suresh.", suspicious=True,
        created_by_pipeline="CDR Parser"),
    EntityRelationship(
        id="rel-suresh-arun", source_id="ent-suresh", source_type="person",
        target_id="ent-arun", target_type="person", rel_type="CALLS",
        case_ids=["case-205"], confidence=70, occurrences=5,
        evidence_ids=[], source="CDR-205",
        timestamp="2026-06-01", time_from="2026-06-01", time_to="2026-08-01",
        rationale="Communication link between cases.", suspicious=False,
        created_by_pipeline="CDR Parser"),
    EntityRelationship(
        id="rel-acc-transfer", source_id="ent-acc-a101", source_type="account",
        target_id="ent-arun", target_type="person", rel_type="TRANSFERS",
        case_ids=["case-205"], confidence=100, occurrences=3,
        evidence_ids=["doc-tx-205"], source="TX-205",
        timestamp="2026-04-15", time_from="2026-04-01", time_to="2026-05-01",
        rationale="Financial transfer from Account A101 to Arun.", suspicious=True,
        created_by_pipeline="Tx Ledger Parser"),
]

@pytest.fixture()
def relationships(db, entities):
    for r in RELATIONSHIPS:
        db.merge(r)
    db.commit()
    return RELATIONSHIPS


# ---------------------------------------------------------------------------
#  Documents — test evidence files
# ---------------------------------------------------------------------------
FIR_TEXT = (
    "FIR-101: Subject Ravi Kumar contacted Suresh using phone 9876543210 "
    "near Chennai Central. Vehicle TN38AB1234 was observed at the scene. "
    "Account A101 received suspicious transfers."
)

DOCUMENTS = [
    Document(id="doc-fir-101", case_id="case-101", filename="fir_101.json",
             source_type="FIR", storage_path="./uploads/case-101/fir_101.json",
             sha256=hashlib.sha256(FIR_TEXT.encode()).hexdigest(),
             size_bytes=len(FIR_TEXT), uploaded_by="u-arjun",
             uploaded_at=datetime.datetime(2026, 8, 1),
             processing_status="completed", extracted_text=FIR_TEXT),
    Document(id="doc-cdr-101", case_id="case-101", filename="cdr_101.csv",
             source_type="CDR", storage_path="./uploads/case-101/cdr_101.csv",
             sha256="cdr_hash_placeholder",
             size_bytes=512, uploaded_by="u-arjun",
             uploaded_at=datetime.datetime(2026, 8, 5),
             processing_status="completed",
             extracted_text='{"caller":"9876543210","callee":"9876543211","duration":420}'),
    Document(id="doc-tx-205", case_id="case-205", filename="tx_205.json",
             source_type="TRANSACTIONS", storage_path="./uploads/case-205/tx_205.json",
             sha256="tx_hash_placeholder",
             size_bytes=256, uploaded_by="u-lena",
             uploaded_at=datetime.datetime(2026, 8, 10),
             processing_status="completed",
             extracted_text='{"sender":"A101","receiver":"Arun","amount":350000}'),
]

@pytest.fixture()
def documents(db, cases):
    for d in DOCUMENTS:
        db.merge(d)
    db.commit()
    return DOCUMENTS


# ---------------------------------------------------------------------------
#  RAG chunks — pre-indexed for retrieval testing
# ---------------------------------------------------------------------------
@pytest.fixture()
def rag_chunks(db, documents):
    from app.services.rag.rag_service import RAGService
    rag = RAGService(db)
    rag.chunk_document("doc-fir-101", "case-101", FIR_TEXT, source_type="FIR")
    return rag


# ---------------------------------------------------------------------------
#  Findings — for pattern tests
# ---------------------------------------------------------------------------
@pytest.fixture()
def findings(db, entities, relationships):
    f = Finding(
        id="fnd-cross-ent-ravi", case_id="case-101",
        category="cross_case_recurrence", title="Cross-case recurrence",
        severity="high", confidence=90,
        why="Entity 'Ravi Kumar' appears in case-101 and case-205.",
        entity_ids=["ent-ravi"], evidence_ids=["doc-fir-101"],
        status="open", created_at=datetime.datetime(2026, 8, 15))
    db.merge(f)
    db.commit()
    return [f]


# ---------------------------------------------------------------------------
#  Temporary file helpers — create real files for parser tests
# ---------------------------------------------------------------------------
@pytest.fixture()
def tmp_dir():
    d = tempfile.mkdtemp(prefix="nexusci_test_")
    yield d
    import shutil
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture()
def fir_json_file(tmp_dir):
    path = os.path.join(tmp_dir, "fir_test.json")
    data = {
        "fir_no": "FIR-TEST-001",
        "police_station": "Central Station PS",
        "date": "2026-08-01",
        "complaint_text": FIR_TEXT,
        "suspects": [
            {"name": "Ravi Kumar", "phone": "9876543210", "vehicle": "TN38AB1234"}
        ]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


@pytest.fixture()
def cdr_csv_file(tmp_dir):
    path = os.path.join(tmp_dir, "cdr_test.csv")
    rows = [
        {"caller": "9876543210", "callee": "9876543211", "duration": "420",
         "timestamp": "2026-03-15T10:30:00", "cell_tower": "Central Tower"},
        {"caller": "9876543211", "callee": "9876543212", "duration": "60",
         "timestamp": "2026-03-15T11:00:00", "cell_tower": "T Nagar Tower"},
        {"caller": "9876543210", "callee": "9876543212", "duration": "800",
         "timestamp": "2026-03-16T09:00:00", "cell_tower": "Adyar Tower"},
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    return path


@pytest.fixture()
def tx_json_file(tmp_dir):
    path = os.path.join(tmp_dir, "tx_test.json")
    data = [
        {"tx_id": "TX-001", "sender": "A101", "receiver": "A201",
         "amount": 350000, "currency": "INR", "timestamp": "2026-04-15"},
        {"tx_id": "TX-002", "sender": "A201", "receiver": "A301",
         "amount": 340000, "currency": "INR", "timestamp": "2026-04-16"},
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


@pytest.fixture()
def fir_txt_file(tmp_dir):
    path = os.path.join(tmp_dir, "fir_report.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(FIR_TEXT)
    return path


@pytest.fixture()
def test_pdf_file(tmp_dir):
    """Creates a real minimal PDF with known text using PyMuPDF."""
    path = os.path.join(tmp_dir, "fir_test.pdf")
    try:
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), FIR_TEXT, fontsize=11)
        doc.save(path)
        doc.close()
        return path
    except Exception:
        # Fallback: write a plain text file with .pdf extension for graceful test skip
        with open(path, "wb") as f:
            f.write(b"%PDF-1.0\ntest")
        return path


@pytest.fixture()
def test_image_file(tmp_dir):
    """Creates a simple PNG image with text for OCR testing."""
    path = os.path.join(tmp_dir, "test_ocr.png")
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (600, 200), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((20, 40), "Ravi Kumar phone 9876543210", fill="black")
        draw.text((20, 80), "Vehicle TN38AB1234", fill="black")
        img.save(path)
        return path
    except Exception:
        return None


# ---------------------------------------------------------------------------
#  Full seeded DB — convenience fixture combining all above
# ---------------------------------------------------------------------------
@pytest.fixture()
def seeded_db(db, users, cases, entities, relationships, documents, findings):
    """Returns a fully seeded in-memory database session."""
    return db
