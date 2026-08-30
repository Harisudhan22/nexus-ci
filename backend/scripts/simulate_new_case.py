import os
import sys
import uuid
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.postgres import SessionLocal, init_db
from app.models.models import Case, Document, CanonicalEntity, EntityRelationship, Finding, RawMention, AuditLog
from app.services.ingestion.coordinator import PipelineCoordinator

def simulate_new_case():
    print("Simulating arrival of NEW Case: CASE-501 (Operation Cyber Shield)...")
    init_db()
    db = SessionLocal()

    case_id = "case-501"
    existing = db.query(Case).filter(Case.id == case_id).first()
    if not existing:
        new_case = Case(
            id=case_id,
            title="Operation Cyber Shield",
            description="Inter-state cyber phishing and unauthorized SIM routing syndicate intercepted in Chennai.",
            status="active",
            priority="critical",
            agency="State Crime Branch",
            classification="SECRET",
            police_station="Central Station PS",
            district="Chennai",
            state="Tamil Nadu",
            assigned_to="u-mira"
        )
        db.add(new_case)
        db.commit()
        print(f"Created new case: {case_id}")
    else:
        print(f"Case {case_id} already exists.")

    # Create new FIR evidence document referencing R. Kumar, 9876543210, TN01AB1234
    doc_id = "FIR-501"
    os.makedirs(f"./uploads/{case_id}", exist_ok=True)
    doc_path = f"./uploads/{case_id}/FIR_501_CyberShield.pdf"
    content_text = """FIRST INFORMATION REPORT (FIR-501/2026)
Police Station: Central Station PS, District: Chennai City
Subject: Cyber Fraud and Hawala Transfer Interception

Incident Details:
On 2026-08-28 at 22:30 hours, surveillance patrol at Central Station intercepted suspect R. Kumar driving a white sedan bearing registration plate TN01AB1234. Subject was found in possession of mobile handset operating phone number 9876543210. 

Preliminary inquiry reveals R. Kumar coordinated fund transfers linking bank account A101 to multiple remote accounts. Associate Arun was observed in vicinity of Central Station parking.

Evidence Recovered:
- Mobile Phone (IMEI: 864209123456789, MSISDN: 9876543210)
- Vehicle: Maruti Swift, White, Registration TN01AB1234
- Banking Slip indicating deposit into Account A101"""

    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(content_text)

    existing_doc = db.query(Document).filter(Document.id == doc_id).first()
    if not existing_doc:
        doc = Document(
            id=doc_id,
            case_id=case_id,
            filename="FIR_501_CyberShield.pdf",
            source_type="FIR",
            storage_path=doc_path,
            sha256="501abc57b123d4e8c1b2c3d4f5e6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4",
            size_bytes=len(content_text.encode("utf-8")),
            uploaded_by="u-mira",
            processing_status="queued",
            extracted_text=content_text
        )
        db.add(doc)
        db.commit()
        print(f"Created evidence document: {doc_id}")
    else:
        doc = existing_doc

    # Process document through PipelineCoordinator
    print(f"Running automated analysis & cross-case resolution on {doc_id}...")
    coordinator = PipelineCoordinator(db)
    coordinator.process_document(doc.id)

    # Link cross-case findings
    # Connect to Ravi Kumar canonical entity
    ravi_canon = db.query(CanonicalEntity).filter(CanonicalEntity.id == "ent-ravi").first()
    if ravi_canon and case_id not in ravi_canon.case_ids:
        c_list = list(ravi_canon.case_ids)
        c_list.append(case_id)
        ravi_canon.case_ids = c_list
        db.commit()

    # Add cross-case convergence finding
    existing_fnd = db.query(Finding).filter(Finding.id == "fnd-501-cross-convergence").first()
    if not existing_fnd:
        fnd = Finding(
            id="fnd-501-cross-convergence",
            case_id=case_id,
            category="cross_case_recurrence",
            title="Multi-Case Entity Convergence Detected",
            severity="high",
            confidence=96,
            why="Entity 'R. Kumar' and phone '9876543210' with vehicle 'TN01AB1234' matches target Ravi Kumar across 5 prior historical operations (case-101, case-203, case-205, case-301, case-412).",
            entity_ids=["ent-ravi", "ent-phone-ravi", "ent-veh-ravi", "ent-acc-a101"],
            evidence_ids=[doc_id, "FIR-101-01", "FIR-205-01", "SRV-01"],
            status="open"
        )
        db.add(fnd)
        db.commit()

    # Audit log
    db.add(AuditLog(
        id=f"aud-{uuid.uuid4().hex[:8]}",
        user_id="u-mira",
        action="CASE_CREATE",
        case_id=case_id,
        resource=f"New Case {case_id} Ingested & Analyzed",
        result="success"
    ))
    db.commit()
    db.close()
    print(f"Simulation of {case_id} completed successfully! Cross-case matches established.")

if __name__ == "__main__":
    simulate_new_case()
