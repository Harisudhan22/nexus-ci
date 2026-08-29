import os
import sys
import uuid
import datetime

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.postgres import SessionLocal, Base, engine
from app.db.neo4j_db import neo4j_client
from app.core.security import get_password_hash
from app.models.models import User, Case, CanonicalEntity, Document, RawMention, Finding, AuditLog, EntityMergeDecision
from app.services.graph.graph_service import Neo4jGraphService

def seed_databases():
    print("Seeding PostgreSQL...")
    db = SessionLocal()
    
    # 1. Recreate schemas to apply column nullability updates
    db.close()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 2. Seed Users
    hashed_password = get_password_hash("demo1234")
    
    users = [
        User(id="u-mira", name="Insp. Mira Rao", email="mira.rao@nexus.gov", username="mira", password_hash=hashed_password, role="senior_investigator", agency_id="State Crime Branch", clearance="SECRET", active=True),
        User(id="u-arjun", name="SI. Arjun Nair", email="arjun.nair@nexus.gov", username="arjun", password_hash=hashed_password, role="investigator", agency_id="State Crime Branch", clearance="CONFIDENTIAL", active=True),
        User(id="u-lena", name="Lena Fernandes", email="lena.fernandes@nexus.gov", username="lena", password_hash=hashed_password, role="analyst", agency_id="Financial Intelligence Unit", clearance="CONFIDENTIAL", active=True),
        User(id="u-dev", name="DySP. Dev Menon", email="dev.menon@nexus.gov", username="dev", password_hash=hashed_password, role="supervisor", agency_id="State Crime Branch", clearance="SECRET", active=True),
        User(id="u-admin", name="System Administrator", email="admin@nexus.gov", username="admin", password_hash=hashed_password, role="admin", agency_id="NEXUS-CI Operations", clearance="SECRET", active=True),
    ]
    for u in users:
        db.add(u)
    db.commit()

    # 3. Seed Cases
    cases = [
        Case(id="case-101", title="Operation Shadow Net", description="Investigation into organized cyber-fraud and local support modules in Chennai.", status="active", priority="high", agency="State Crime Branch", classification="SECRET", assigned_to="u-mira"),
        Case(id="case-205", title="Hawala Syndicate Alpha", description="Cross-border financial transactions linking suspicious import channels.", status="active", priority="critical", agency="Financial Intelligence Unit", classification="SECRET", assigned_to="u-lena"),
    ]
    for c in cases:
        db.add(c)
    db.commit()

    # 4. Seed Canonical Entities
    entities = [
        # Person
        CanonicalEntity(id="ent-ravi", type="person", label="Ravi Kumar", subtitle="Primary Investigative Target", case_ids=["case-101", "case-205"], aliases=["Ravi Kumar", "RAVI KUMAR", "R. Kumar"], relevance=88, attributes={"Clearance": "None", "Occupation": "Merchant", "State": "Tamil Nadu"}, cluster="cluster_1", x=420.0, y=280.0),
        CanonicalEntity(id="ent-arun", type="person", label="Arun", subtitle="Secondary Associate", case_ids=["case-101"], aliases=["Arun"], relevance=70, attributes={"Occupation": "Driver"}, cluster="cluster_1", x=240.0, y=180.0),
        
        # Phone
        CanonicalEntity(id="ent-phone", type="phone", label="9876543210", subtitle="Suspect Device", case_ids=["case-101"], aliases=["9876543210"], relevance=80, attributes={"Provider": "Jio", "Location": "Chennai"}, cluster="cluster_1", x=420.0, y=100.0),
        
        # Vehicle
        CanonicalEntity(id="ent-vehicle", type="vehicle", label="TN01AB1234", subtitle="Suspect Sedan", case_ids=["case-101"], aliases=["TN01AB1234"], relevance=75, attributes={"Model": "Swift", "Color": "White"}, cluster="cluster_1", x=180.0, y=340.0),
        
        # Account
        CanonicalEntity(id="ent-account", type="account", label="A101", subtitle="Suspicious Bank Account", case_ids=["case-101", "case-205"], aliases=["A101", "ACC-101"], relevance=90, attributes={"Bank": "SBI", "Branch": "Central Branch"}, cluster="cluster_2", x=680.0, y=280.0),
        
        # Location
        CanonicalEntity(id="ent-location", type="location", label="Central Station", subtitle="Meeting Point", case_ids=["case-101"], aliases=["Central Station"], relevance=65, attributes={"City": "Chennai"}, cluster="cluster_2", x=680.0, y=450.0),
    ]
    for e in entities:
        db.add(e)
    db.commit()

    # 5. Seed Documents
    docs = [
        Document(id="FIR-101", case_id="case-101", filename="FIR_101_ShadowNet.pdf", source_type="FIR", storage_path="./uploads/case-101/FIR_101_ShadowNet.pdf", sha256="4fa72c57b123d4e8c1b2c3d4f5e6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4", size_bytes=10240, uploaded_by="u-mira", uploaded_at=datetime.datetime.utcnow() - datetime.timedelta(days=5), processing_status="completed", extracted_text="First Information Report (FIR) lodged at Central Station. Primary suspect Ravi Kumar, associated with Arun. Suspect has been spotted driving a white Swift sedan bearing registration plate TN01AB1234. Target phone contact identified as 9876543210. Target Ravi Kumar uses bank account A101 for local transactions."),
        Document(id="CDR-101", case_id="case-101", filename="CDR_101_Ravi.csv", source_type="CDR", storage_path="./uploads/case-101/CDR_101_Ravi.csv", sha256="9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c", size_bytes=512, uploaded_by="u-mira", uploaded_at=datetime.datetime.utcnow() - datetime.timedelta(days=4), processing_status="completed", extracted_text="Caller,Callee,Duration,Timestamp\n9876543210,9876543211,120,2026-08-20T10:15:00\n9876543210,Ravi Kumar,320,2026-08-20T11:30:00", rows_data=[
            {"caller": "9876543210", "callee": "Ravi Kumar", "duration": "320", "timestamp": "2026-08-20T11:30:00"},
            {"caller": "9876543210", "callee": "9876543211", "duration": "120", "timestamp": "2026-08-20T10:15:00"}
        ]),
        Document(id="TX-101", case_id="case-101", filename="TX_101_Ledger.csv", source_type="TRANSACTIONS", storage_path="./uploads/case-101/TX_101_Ledger.csv", sha256="e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8", size_bytes=768, uploaded_by="u-lena", uploaded_at=datetime.datetime.utcnow() - datetime.timedelta(days=2), processing_status="completed", extracted_text="Sender,Receiver,Amount,Timestamp\nRavi Kumar,A101,150000,2026-08-21T14:45:00\nA101,Account X,120000,2026-08-21T16:00:00", rows_data=[
            {"sender": "Ravi Kumar", "receiver": "A101", "amount": "150000", "timestamp": "2026-08-21T14:45:00"},
            {"sender": "A101", "receiver": "Account X", "amount": "120000", "timestamp": "2026-08-21T16:00:00"}
        ])
    ]
    for d in docs:
        db.add(d)
    db.commit()

    # 6. Seed Raw Mentions
    mentions = [
        RawMention(id="raw-1", case_id="case-101", evidence_id="FIR-101", surface="Ravi Kumar", type="person", resolved_to="ent-ravi"),
        RawMention(id="raw-2", case_id="case-101", evidence_id="FIR-101", surface="Arun", type="person", resolved_to="ent-arun"),
        RawMention(id="raw-3", case_id="case-101", evidence_id="FIR-101", surface="TN01AB1234", type="vehicle", resolved_to="ent-vehicle"),
        RawMention(id="raw-4", case_id="case-101", evidence_id="FIR-101", surface="9876543210", type="phone", resolved_to="ent-phone"),
        RawMention(id="raw-5", case_id="case-101", evidence_id="FIR-101", surface="A101", type="account", resolved_to="ent-account"),
    ]
    for m in mentions:
        db.add(m)
    db.commit()

    # 7. Seed Resolution Candidate (duplicate entity R. Kumar pending merge to Ravi Kumar)
    cand = EntityMergeDecision(
        id="cand-rkumar-ravi",
        case_id="case-101",
        canonical_id="ent-ravi",
        canonical_label="Ravi Kumar",
        type="person",
        mentions=["R. Kumar"],
        confidence=91,
        signals=[
            {"label": "Name similarity", "matched": True},
            {"label": "Phone match", "matched": True},
            {"label": "Vehicle association", "matched": True},
            {"label": "Case overlap", "matched": True}
        ],
        status="pending"
    )
    db.add(cand)
    db.commit()

    # 8. Seed Findings
    findings = [
        Finding(id="fnd-bridge-ravi", case_id="case-101", category="potential_bridge", title="Potential bridge", severity="high", confidence=88, why="Connects two otherwise separate network clusters (Phone logs and Transaction networks).", entity_ids=["ent-ravi"], evidence_ids=["FIR-101", "CDR-101", "TX-101"], status="open", created_at=datetime.datetime.utcnow() - datetime.timedelta(days=2)),
        Finding(id="fnd-cross-ravi", case_id="case-101", category="cross_case_recurrence", title="Cross-case recurrence", severity="high", confidence=90, why="Identified target Ravi Kumar appears across both Operation Shadow Net and Hawala Syndicate Alpha.", entity_ids=["ent-ravi"], evidence_ids=[], status="open", created_at=datetime.datetime.utcnow() - datetime.timedelta(days=1)),
    ]
    for f in findings:
        db.add(f)
    db.commit()

    # 9. Seed Audit Logs
    audits = [
        AuditLog(id="a-1", timestamp=datetime.datetime.utcnow() - datetime.timedelta(hours=12), user_id="u-mira", action="LOGIN", resource="Session", result="success"),
        AuditLog(id="a-2", timestamp=datetime.datetime.utcnow() - datetime.timedelta(hours=10), user_id="u-mira", action="VIEW", case_id="case-101", resource="Case overview", result="success"),
        AuditLog(id="a-3", timestamp=datetime.datetime.utcnow() - datetime.timedelta(hours=9), user_id="u-mira", action="UPLOAD", case_id="case-101", resource="CDR_101_Ravi.csv", result="success"),
    ]
    for a in audits:
        db.add(a)
    db.commit()

    db.close()
    print("PostgreSQL seeded successfully.")

    # 10. Seed Neo4j Graph
    print("Seeding Neo4j Knowledge Graph...")
    try:
        neo4j_client.connect()
        session = neo4j_client.get_session()
        service = Neo4jGraphService(session)
        
        # Clear graph database
        service.clear_db()
        
        # Create Nodes
        service.create_entity_node("ent-ravi", "person", "Ravi Kumar", ["case-101", "case-205"], "cluster_1", {"Clearance": "None", "Occupation": "Merchant", "State": "Tamil Nadu"})
        service.create_entity_node("ent-arun", "person", "Arun", ["case-101"], "cluster_1", {"Occupation": "Driver"})
        service.create_entity_node("ent-phone", "phone", "9876543210", ["case-101"], "cluster_1", {"Provider": "Jio", "Location": "Chennai"})
        service.create_entity_node("ent-vehicle", "vehicle", "TN01AB1234", ["case-101"], "cluster_1", {"Model": "Swift", "Color": "White"})
        service.create_entity_node("ent-account", "account", "A101", ["case-101", "case-205"], "cluster_2", {"Bank": "SBI", "Branch": "Central Branch"})
        service.create_entity_node("ent-location", "location", "Central Station", ["case-101"], "cluster_2", {"City": "Chennai"})
        service.create_entity_node("FIR-101", "document", "FIR_101_ShadowNet.pdf", ["case-101"], "cluster_2")
        service.create_entity_node("CDR-101", "document", "CDR_101_Ravi.csv", ["case-101"], "cluster_2")
        service.create_entity_node("TX-101", "document", "TX_101_Ledger.csv", ["case-101"], "cluster_2")

        # Create Relationships with Provenance
        # Phone CALLS Ravi
        service.create_relationship(
            source_id="ent-phone", source_type="phone",
            target_id="ent-ravi", target_type="person",
            rel_type="CALLS",
            properties={
                "confidence": 95,
                "evidence_ids": ["CDR-101"],
                "source": "CDR_101_Ravi.csv",
                "timestamp": "2026-08-20T11:30:00",
                "time_from": "2026-08-20T11:30:00",
                "time_to": "2026-08-20T11:30:00",
                "created_by_pipeline": "CDR Parser",
                "occurrences": 5,
                "suspicious": True,
                "rationale": "High-frequency call logging to target suspect device."
            }
        )

        # Ravi OWNS Phone
        service.create_relationship(
            source_id="ent-ravi", source_type="person",
            target_id="ent-phone", target_type="phone",
            rel_type="OWNS",
            properties={
                "confidence": 90,
                "evidence_ids": ["FIR-101"],
                "source": "FIR_101_ShadowNet.pdf",
                "created_by_pipeline": "FIR Extraction",
                "occurrences": 1,
                "rationale": "FIR states 9876543210 is registered to target suspect Ravi Kumar."
            }
        )

        # Ravi TRANSFERS Account
        service.create_relationship(
            source_id="ent-ravi", source_type="person",
            target_id="ent-account", target_type="account",
            rel_type="TRANSFERS",
            properties={
                "confidence": 100,
                "evidence_ids": ["TX-101"],
                "source": "TX_101_Ledger.csv",
                "timestamp": "2026-08-21T14:45:00",
                "time_from": "2026-08-21T14:45:00",
                "time_to": "2026-08-21T14:45:00",
                "created_by_pipeline": "Tx Ledger Parser",
                "occurrences": 1,
                "suspicious": True,
                "rationale": "Substantial financial transaction transfer from suspect target."
            }
        )

        # Ravi ASSOCIATED_WITH Arun
        service.create_relationship(
            source_id="ent-ravi", source_type="person",
            target_id="ent-arun", target_type="person",
            rel_type="ASSOCIATED_WITH",
            properties={
                "confidence": 85,
                "evidence_ids": ["FIR-101"],
                "source": "FIR_101_ShadowNet.pdf",
                "created_by_pipeline": "FIR Extraction",
                "occurrences": 1,
                "rationale": "FIR notes target Ravi Kumar co-operates and meets with Arun."
            }
        )

        # Arun OWNS Vehicle
        service.create_relationship(
            source_id="ent-arun", source_type="person",
            target_id="ent-vehicle", target_type="vehicle",
            rel_type="OWNS",
            properties={
                "confidence": 90,
                "evidence_ids": ["FIR-101"],
                "source": "FIR_101_ShadowNet.pdf",
                "created_by_pipeline": "FIR Extraction",
                "occurrences": 1,
                "rationale": "FIR notes Arun owns whiteSwift sedan registration plate TN01AB1234."
            }
        )

        # Vehicle SEEN_AT Location
        service.create_relationship(
            source_id="ent-vehicle", source_type="vehicle",
            target_id="ent-location", target_type="location",
            rel_type="SEEN_AT",
            properties={
                "confidence": 80,
                "evidence_ids": ["FIR-101"],
                "source": "FIR_101_ShadowNet.pdf",
                "created_by_pipeline": "FIR Extraction",
                "occurrences": 1,
                "rationale": "Sedan vehicle spotted parked in vicinity of Central Station."
            }
        )

        session.close()
        print("Neo4j seeded successfully.")
    except Exception as e:
        print(f"Skipping Neo4j seed because Neo4j is offline or auth failed: {e}")

if __name__ == "__main__":
    seed_databases()
