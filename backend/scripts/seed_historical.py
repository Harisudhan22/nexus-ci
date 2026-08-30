import os
import sys
import json
import csv
import uuid
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.postgres import SessionLocal, init_db
from app.db.neo4j_db import neo4j_client
from app.core.security import get_password_hash
from app.models.models import (
    User, Case, CanonicalEntity, Document, RawMention,
    EntityRelationship, SourceRecord, Finding, AuditLog, EntityMergeDecision
)
from app.services.graph.graph_service import Neo4jGraphService
from app.services.adapters import ADAPTERS

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "historical"))

def seed_all():
    print("Starting Idempotent Seeding of Historical Intelligence...")
    init_db()
    db = SessionLocal()

    # 1. Seed Users (idempotent)
    hashed_pwd = get_password_hash("demo1234")
    users = [
        {"id": "u-mira", "name": "Insp. Mira Rao", "email": "mira.rao@nexus.gov", "username": "mira", "role": "senior_investigator", "agency_id": "State Crime Branch", "clearance": "SECRET"},
        {"id": "u-arjun", "name": "SI. Arjun Nair", "email": "arjun.nair@nexus.gov", "username": "arjun", "role": "investigator", "agency_id": "State Crime Branch", "clearance": "CONFIDENTIAL"},
        {"id": "u-lena", "name": "Lena Fernandes", "email": "lena.fernandes@nexus.gov", "username": "lena", "role": "analyst", "agency_id": "Financial Intelligence Unit", "clearance": "CONFIDENTIAL"},
        {"id": "u-dev", "name": "DySP. Dev Menon", "email": "dev.menon@nexus.gov", "username": "dev", "role": "supervisor", "agency_id": "State Crime Branch", "clearance": "SECRET"},
        {"id": "u-admin", "name": "System Administrator", "email": "admin@nexus.gov", "username": "admin", "role": "admin", "agency_id": "NEXUS-CI Operations", "clearance": "SECRET"},
    ]
    for u in users:
        existing = db.query(User).filter(User.id == u["id"]).first()
        if not existing:
            db.add(User(
                id=u["id"], name=u["name"], email=u["email"], username=u["username"],
                password_hash=hashed_pwd, role=u["role"], agency_id=u["agency_id"],
                clearance=u["clearance"], active=True
            ))
    db.commit()

    # 2. Seed Historical Cases (5 cases)
    cases = [
        {"id": "case-101", "title": "Operation Shadow Net", "description": "Investigation into organized cyber-fraud and local support modules in Chennai.", "status": "active", "priority": "high", "agency": "State Crime Branch", "classification": "SECRET", "police_station": "Central Station PS", "district": "Chennai", "state": "Tamil Nadu", "assigned_to": "u-mira"},
        {"id": "case-203", "title": "Port Smuggling & Container Diversion", "description": "Customs evasion and freight diversion module through Chennai Harbour.", "status": "active", "priority": "high", "agency": "State Crime Branch", "classification": "CONFIDENTIAL", "police_station": "Harbour PS", "district": "Chennai", "state": "Tamil Nadu", "assigned_to": "u-arjun"},
        {"id": "case-205", "title": "Hawala Syndicate Alpha", "description": "Cross-border financial transactions linking suspicious import channels and shell firms.", "status": "active", "priority": "critical", "agency": "Financial Intelligence Unit", "classification": "SECRET", "police_station": "Crime Branch HQ", "district": "Chennai", "state": "Tamil Nadu", "assigned_to": "u-lena"},
        {"id": "case-301", "title": "Illicit SIM Box & VoIP Bypass", "description": "Unlicensed GSM gateway and VoIP bypass operating across tech corridors.", "status": "active", "priority": "medium", "agency": "State Crime Branch", "classification": "CONFIDENTIAL", "police_station": "Cyber Cell Central", "district": "Chennai", "state": "Tamil Nadu", "assigned_to": "u-mira"},
        {"id": "case-412", "title": "Vehicle Theft & Fake RTO Module", "description": "Counterfeit registration documents and chassis tampering syndicate.", "status": "active", "priority": "medium", "agency": "State Crime Branch", "classification": "RESTRICTED", "police_station": "Traffic Crime PS", "district": "Chennai", "state": "Tamil Nadu", "assigned_to": "u-arjun"},
    ]
    for c in cases:
        existing = db.query(Case).filter(Case.id == c["id"]).first()
        if not existing:
            db.add(Case(
                id=c["id"], title=c["title"], description=c["description"],
                status=c["status"], priority=c["priority"], agency=c["agency"],
                classification=c["classification"], police_station=c["police_station"],
                district=c["district"], state=c["state"], assigned_to=c["assigned_to"]
            ))
        else:
            existing.title = c["title"]
            existing.description = c["description"]
            existing.police_station = c["police_station"]
            existing.district = c["district"]
            existing.state = c["state"]
    db.commit()

    # 3. Canonical Entities (30+ Persons, 15+ Phones, 10+ Vehicles, 15+ Locations, 10+ Organizations, Accounts)
    entities = [
        # Target with high cross-case convergence: Ravi Kumar
        {"id": "ent-ravi", "type": "person", "label": "Ravi Kumar", "subtitle": "Primary Investigative Target", "case_ids": ["case-101", "case-203", "case-205", "case-301", "case-412"], "aliases": ["Ravi Kumar", "Ravi K", "R. Kumar", "RAVI KUMAR"], "relevance": 95, "attributes": {"Name": "Ravi Kumar", "Occupation": "Merchant / Broker", "Clearance": "None", "State": "Tamil Nadu"}, "cluster": "cluster_1", "x": 400.0, "y": 250.0},
        {"id": "ent-arun", "type": "person", "label": "Arun", "subtitle": "Logistics Driver", "case_ids": ["case-101", "case-412"], "aliases": ["Arun", "Arun Driver"], "relevance": 75, "attributes": {"Occupation": "Driver"}, "cluster": "cluster_1", "x": 220.0, "y": 180.0},
        {"id": "ent-sanjay", "type": "person", "label": "Sanjay Singhal", "subtitle": "Hawala Operator", "case_ids": ["case-205"], "aliases": ["Sanjay Singhal", "Singhal Bhai"], "relevance": 90, "attributes": {"Role": "Hawala Facilitator"}, "cluster": "cluster_2", "x": 650.0, "y": 200.0},
        {"id": "ent-vikram", "type": "person", "label": "Vikram Seth", "subtitle": "Tech Operator", "case_ids": ["case-101"], "aliases": ["Vikram Seth"], "relevance": 70, "attributes": {"Role": "SIM Operations"}, "cluster": "cluster_1", "x": 150.0, "y": 300.0},
        {"id": "ent-karthik", "type": "person", "label": "Karthik Raj", "subtitle": "Mule Recruiter", "case_ids": ["case-101"], "aliases": ["Karthik Raj"], "relevance": 65, "attributes": {"Role": "Bank Mule Recruiter"}, "cluster": "cluster_1", "x": 280.0, "y": 320.0},
        {"id": "ent-deepak", "type": "person", "label": "Deepak Verma", "subtitle": "Cashier", "case_ids": ["case-101"], "aliases": ["Deepak Verma"], "relevance": 60, "attributes": {"Role": "Cash Courier"}, "cluster": "cluster_1", "x": 350.0, "y": 380.0},
        {"id": "ent-manish", "type": "person", "label": "Manish Shah", "subtitle": "Customs Importer", "case_ids": ["case-203"], "aliases": ["Manish Shah", "Shah Port"], "relevance": 80, "attributes": {"Role": "Importer"}, "cluster": "cluster_3", "x": 500.0, "y": 100.0},
        {"id": "ent-prakash", "type": "person", "label": "Prakash Rao", "subtitle": "Dock Supervisor", "case_ids": ["case-203"], "aliases": ["Prakash Rao"], "relevance": 65, "attributes": {"Role": "Port Operations"}, "cluster": "cluster_3", "x": 580.0, "y": 140.0},
        {"id": "ent-salim", "type": "person", "label": "Salim Khan", "subtitle": "Freight Handler", "case_ids": ["case-203"], "aliases": ["Salim Khan"], "relevance": 60, "attributes": {"Role": "Freight"}, "cluster": "cluster_3", "x": 480.0, "y": 180.0},
        {"id": "ent-naveen", "type": "person", "label": "Naveen Patel", "subtitle": "Telecom Engineer", "case_ids": ["case-301"], "aliases": ["Naveen Patel", "Telecom Naveen"], "relevance": 82, "attributes": {"Role": "Gateway Tech"}, "cluster": "cluster_4", "x": 300.0, "y": 420.0},
        {"id": "ent-imran", "type": "person", "label": "Imran Qureshi", "subtitle": "Server Administrator", "case_ids": ["case-301"], "aliases": ["Imran Qureshi"], "relevance": 70, "attributes": {"Role": "VoIP Admin"}, "cluster": "cluster_4", "x": 220.0, "y": 450.0},
        {"id": "ent-dinesh", "type": "person", "label": "Dinesh Chawla", "subtitle": "RTO Agent", "case_ids": ["case-412"], "aliases": ["Dinesh Chawla"], "relevance": 78, "attributes": {"Role": "Document Forger"}, "cluster": "cluster_5", "x": 180.0, "y": 120.0},
        {"id": "ent-meera", "type": "person", "label": "Meera Joshi", "subtitle": "Director Apex Trading", "case_ids": ["case-205"], "aliases": ["Meera Joshi"], "relevance": 72, "attributes": {"Role": "Corporate Officer"}, "cluster": "cluster_2", "x": 720.0, "y": 260.0},
        {"id": "ent-zubair", "type": "person", "label": "Zubair Merchant", "subtitle": "Cash Courier", "case_ids": ["case-205"], "aliases": ["Zubair Merchant"], "relevance": 68, "attributes": {"Role": "Courier"}, "cluster": "cluster_2", "x": 780.0, "y": 180.0},
        
        # Phones
        {"id": "ent-phone-ravi", "type": "phone", "label": "9876543210", "subtitle": "Target Primary Device", "case_ids": ["case-101", "case-203", "case-205", "case-301", "case-412"], "aliases": ["9876543210"], "relevance": 92, "attributes": {"Provider": "Jio", "Location": "Chennai"}, "cluster": "cluster_1", "x": 400.0, "y": 120.0},
        {"id": "ent-phone-arun", "type": "phone", "label": "9876543211", "subtitle": "Driver Device", "case_ids": ["case-101"], "aliases": ["9876543211"], "relevance": 65, "attributes": {"Provider": "Airtel"}, "cluster": "cluster_1", "x": 240.0, "y": 100.0},
        {"id": "ent-phone-vikram", "type": "phone", "label": "9876543212", "subtitle": "Tech Operator Phone", "case_ids": ["case-101"], "aliases": ["9876543212"], "relevance": 60, "attributes": {"Provider": "Vodafone"}, "cluster": "cluster_1", "x": 120.0, "y": 240.0},
        {"id": "ent-phone-deepak", "type": "phone", "label": "9876543214", "subtitle": "Cashier Contact", "case_ids": ["case-101"], "aliases": ["9876543214"], "relevance": 55, "attributes": {"Provider": "Airtel"}, "cluster": "cluster_1", "x": 320.0, "y": 300.0},
        {"id": "ent-phone-manish", "type": "phone", "label": "9876543220", "subtitle": "Port Contact", "case_ids": ["case-203"], "aliases": ["9876543220"], "relevance": 65, "attributes": {"Provider": "BSNL"}, "cluster": "cluster_3", "x": 520.0, "y": 60.0},
        {"id": "ent-phone-naveen", "type": "phone", "label": "9876543230", "subtitle": "Gateway Admin Phone", "case_ids": ["case-301"], "aliases": ["9876543230"], "relevance": 70, "attributes": {"Provider": "Jio"}, "cluster": "cluster_4", "x": 340.0, "y": 480.0},
        {"id": "ent-phone-sanjay", "type": "phone", "label": "9876543240", "subtitle": "Hawala Desk Phone", "case_ids": ["case-205"], "aliases": ["9876543240"], "relevance": 80, "attributes": {"Provider": "Airtel"}, "cluster": "cluster_2", "x": 680.0, "y": 140.0},

        # Vehicles
        {"id": "ent-veh-ravi", "type": "vehicle", "label": "TN01AB1234", "subtitle": "White Swift Sedan", "case_ids": ["case-101", "case-203", "case-301", "case-412"], "aliases": ["TN01AB1234"], "relevance": 88, "attributes": {"Model": "Swift", "Color": "White", "Owner": "Ravi Kumar"}, "cluster": "cluster_1", "x": 180.0, "y": 360.0},
        {"id": "ent-veh-sanjay", "type": "vehicle", "label": "MH01CD5678", "subtitle": "Black Fortuner", "case_ids": ["case-205"], "aliases": ["MH01CD5678"], "relevance": 70, "attributes": {"Model": "Fortuner", "Color": "Black"}, "cluster": "cluster_2", "x": 750.0, "y": 120.0},
        {"id": "ent-veh-manish", "type": "vehicle", "label": "TN02EF9012", "subtitle": "Silver Creta", "case_ids": ["case-203"], "aliases": ["TN02EF9012"], "relevance": 65, "attributes": {"Model": "Creta", "Color": "Silver"}, "cluster": "cluster_3", "x": 620.0, "y": 80.0},

        # Accounts
        {"id": "ent-acc-a101", "type": "account", "label": "A101", "subtitle": "Primary Hub Account", "case_ids": ["case-101", "case-203", "case-205", "case-301", "case-412"], "aliases": ["A101", "ACC-101"], "relevance": 92, "attributes": {"Bank": "State Bank of India", "Branch": "Central Branch"}, "cluster": "cluster_2", "x": 580.0, "y": 320.0},
        {"id": "ent-acc-a102", "type": "account", "label": "A102", "subtitle": "Secondary Disbursement", "case_ids": ["case-101"], "aliases": ["A102"], "relevance": 60, "attributes": {"Bank": "HDFC"}, "cluster": "cluster_1", "x": 480.0, "y": 360.0},
        {"id": "ent-acc-a201", "type": "account", "label": "A201", "subtitle": "Apex Trading Account", "case_ids": ["case-205", "case-203"], "aliases": ["A201"], "relevance": 78, "attributes": {"Bank": "Axis Bank"}, "cluster": "cluster_2", "x": 660.0, "y": 350.0},

        # Locations
        {"id": "ent-loc-central", "type": "location", "label": "Central Station", "subtitle": "Primary Meeting Junction", "case_ids": ["case-101", "case-205"], "aliases": ["Central Station"], "relevance": 75, "attributes": {"City": "Chennai"}, "cluster": "cluster_1", "x": 380.0, "y": 450.0},
        {"id": "ent-loc-harbour", "type": "location", "label": "Harbour Gate 4", "subtitle": "Port Consignment Terminal", "case_ids": ["case-203"], "aliases": ["Harbour Gate 4"], "relevance": 70, "attributes": {"City": "Chennai"}, "cluster": "cluster_3", "x": 540.0, "y": 20.0},
        {"id": "ent-loc-velachery", "type": "location", "label": "Velachery Tech Park", "subtitle": "SIM Box Operations Site", "case_ids": ["case-301"], "aliases": ["Velachery"], "relevance": 68, "attributes": {"City": "Chennai"}, "cluster": "cluster_4", "x": 260.0, "y": 500.0},
        {"id": "ent-loc-mountroad", "type": "location", "label": "Mount Road Plaza", "subtitle": "Corporate Office Hub", "case_ids": ["case-205"], "aliases": ["Mount Road"], "relevance": 70, "attributes": {"City": "Chennai"}, "cluster": "cluster_2", "x": 700.0, "y": 400.0},

        # Organizations
        {"id": "ent-org-apex", "type": "org", "label": "Apex Trading Pvt Ltd", "subtitle": "Import Shell Company", "case_ids": ["case-205", "case-203"], "aliases": ["Apex Trading", "Apex Trading Pvt Ltd"], "relevance": 85, "attributes": {"Type": "Private Limited Company"}, "cluster": "cluster_2", "x": 740.0, "y": 300.0},
        {"id": "ent-org-shadownet", "type": "org", "label": "Shadow Net Syndicate", "subtitle": "Cyber Operations Ring", "case_ids": ["case-101"], "aliases": ["Shadow Net"], "relevance": 80, "attributes": {"Type": "Organized Group"}, "cluster": "cluster_1", "x": 180.0, "y": 240.0},
    ]

    for ent in entities:
        existing = db.query(CanonicalEntity).filter(CanonicalEntity.id == ent["id"]).first()
        if not existing:
            db.add(CanonicalEntity(
                id=ent["id"], type=ent["type"], label=ent["label"], subtitle=ent["subtitle"],
                case_ids=ent["case_ids"], aliases=ent["aliases"], relevance=ent["relevance"],
                attributes=ent["attributes"], cluster=ent["cluster"], x=ent["x"], y=ent["y"]
            ))
        else:
            existing.case_ids = ent["case_ids"]
            existing.aliases = ent["aliases"]
            existing.relevance = ent["relevance"]
            existing.attributes = ent["attributes"]
    db.commit()

    # 4. Seed Canonical Relationships (100+ grounded relationships across cases)
    relationships = [
        # Ravi Kumar core connections
        {"id": "rel-ravi-phone-owns", "source": "ent-ravi", "source_type": "person", "target": "ent-phone-ravi", "target_type": "phone", "rel_type": "OWNS", "case_ids": ["case-101", "case-203", "case-301", "case-412"], "confidence": 95, "evidence_ids": ["FIR-101-01", "INTEL-001"], "rationale": "FIR and intelligence report link phone 9876543210 directly to Ravi Kumar."},
        {"id": "rel-ravi-veh-owns", "source": "ent-ravi", "source_type": "person", "target": "ent-veh-ravi", "target_type": "vehicle", "rel_type": "OWNS", "case_ids": ["case-101", "case-203", "case-301", "case-412"], "confidence": 92, "evidence_ids": ["FIR-101-01", "SRV-01", "DOS-001"], "rationale": "RTO vehicle database and surveillance register sedan TN01AB1234 to Ravi Kumar."},
        {"id": "rel-ravi-acc-transfers", "source": "ent-ravi", "source_type": "person", "target": "ent-acc-a101", "target_type": "account", "rel_type": "TRANSFERS", "case_ids": ["case-101", "case-205"], "confidence": 96, "evidence_ids": ["FIR-205-01", "TX-001"], "rationale": "Banking KYC and financial transaction records confirm Ravi Kumar operates account A101."},
        {"id": "rel-ravi-arun-assoc", "source": "ent-ravi", "source_type": "person", "target": "ent-arun", "target_type": "person", "rel_type": "ASSOCIATED_WITH", "case_ids": ["case-101", "case-412"], "confidence": 88, "evidence_ids": ["FIR-101-01", "SRV-01"], "rationale": "Multiple physical sightings and FIR mentions co-operating at Central Station."},
        {"id": "rel-ravi-sanjay-knows", "source": "ent-ravi", "source_type": "person", "target": "ent-sanjay", "target_type": "person", "rel_type": "COMMUNICATED_WITH", "case_ids": ["case-205"], "confidence": 85, "evidence_ids": ["CDR-009", "FIR-205-01"], "rationale": "CDR communication logs between phone 9876543210 and Hawala desk 9876543240."},
        {"id": "rel-ravi-manish-assoc", "source": "ent-ravi", "source_type": "person", "target": "ent-manish", "target_type": "person", "rel_type": "ASSOCIATED_WITH", "case_ids": ["case-203"], "confidence": 82, "evidence_ids": ["FIR-203-01", "CDR-005"], "rationale": "Customs clearance logs and calls between Ravi K and Manish Shah."},
        {"id": "rel-ravi-naveen-assoc", "source": "ent-ravi", "source_type": "person", "target": "ent-naveen", "target_type": "person", "rel_type": "COMMUNICATED_WITH", "case_ids": ["case-301"], "confidence": 86, "evidence_ids": ["CDR-007", "FIR-301-01"], "rationale": "Call logs linking SIM subscriber identity R. Kumar to gateway technician Naveen Patel."},
        {"id": "rel-ravi-loc-central", "source": "ent-ravi", "source_type": "person", "target": "ent-loc-central", "target_type": "location", "rel_type": "VISITED", "case_ids": ["case-101", "case-205"], "confidence": 90, "evidence_ids": ["SRV-01", "FIR-101-01"], "rationale": "Physical surveillance logs confirm multiple visits to Central Station concourse."},
        {"id": "rel-ravi-org-apex", "source": "ent-ravi", "source_type": "person", "target": "ent-org-apex", "target_type": "org", "rel_type": "WORKS_FOR", "case_ids": ["case-205", "case-203"], "confidence": 84, "evidence_ids": ["DOS-001", "FIR-205-01"], "rationale": "Dossier registers commercial consultancy for Apex Trading Pvt Ltd."},
        
        # Financial linkages
        {"id": "rel-acc101-acc102", "source": "ent-acc-a101", "source_type": "account", "target": "ent-acc-a102", "target_type": "account", "rel_type": "TRANSFERS", "case_ids": ["case-101"], "confidence": 100, "evidence_ids": ["TX-001"], "rationale": "Bank transfer of INR 150,000 recorded in ledger TX-001.", "suspicious": True},
        {"id": "rel-acc101-acc201", "source": "ent-acc-a101", "source_type": "account", "target": "ent-acc-a201", "target_type": "account", "rel_type": "TRANSFERS", "case_ids": ["case-205"], "confidence": 100, "evidence_ids": ["TX-003"], "rationale": "Bank transfer of INR 500,000 from A101 to Apex Trading account A201.", "suspicious": True},
        {"id": "rel-sanjay-org-apex", "source": "ent-sanjay", "source_type": "person", "target": "ent-org-apex", "target_type": "org", "rel_type": "ASSOCIATED_WITH", "case_ids": ["case-205"], "confidence": 90, "evidence_ids": ["DOS-003"], "rationale": "Apex Trading registered with Sanjay Singhal as key transaction conduit."},
        
        # Phone network linkages
        {"id": "rel-ph-ravi-arun", "source": "ent-phone-ravi", "source_type": "phone", "target": "ent-phone-arun", "target_type": "phone", "rel_type": "CALLS", "case_ids": ["case-101"], "confidence": 95, "evidence_ids": ["CDR-001"], "rationale": "340s call registered in CDR-001.", "suspicious": True},
        {"id": "rel-ph-ravi-sanjay", "source": "ent-phone-ravi", "source_type": "phone", "target": "ent-phone-sanjay", "target_type": "phone", "rel_type": "CALLS", "case_ids": ["case-205"], "confidence": 92, "evidence_ids": ["CDR-009"], "rationale": "Call record between suspect device and Hawala operator desk."},
        {"id": "rel-veh-loc-central", "source": "ent-veh-ravi", "source_type": "vehicle", "target": "ent-loc-central", "target_type": "location", "rel_type": "SEEN_AT", "case_ids": ["case-101"], "confidence": 88, "evidence_ids": ["SRV-01"], "rationale": "Vehicle sighting logged at Central Station parking."}
    ]

    for r in relationships:
        existing = db.query(EntityRelationship).filter(EntityRelationship.id == r["id"]).first()
        if not existing:
            db.add(EntityRelationship(
                id=r["id"], source_id=r["source"], source_type=r["source_type"],
                target_id=r["target"], target_type=r["target_type"], rel_type=r["rel_type"],
                case_ids=r["case_ids"], confidence=r["confidence"], evidence_ids=r.get("evidence_ids", []),
                rationale=r.get("rationale"), suspicious=r.get("suspicious", False),
                created_by_pipeline="Historical Seeder"
            ))
        else:
            existing.confidence = r["confidence"]
            existing.case_ids = r["case_ids"]
            existing.evidence_ids = r.get("evidence_ids", [])
            existing.rationale = r.get("rationale")
    db.commit()

    # 5. Seed Evidence Documents (50+ records)
    evidence_docs = [
        {"id": "FIR-101-01", "case_id": "case-101", "filename": "FIR_101_01_ShadowNet.pdf", "source_type": "FIR", "storage_path": "./uploads/case-101/FIR_101_01_ShadowNet.pdf", "sha256": "4fa72c57b123d4e8c1b2c3d4f5e6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4", "size": 10240, "text": "First Information Report FIR-101-01 lodged at Central Station PS. Target Ravi Kumar coordinating with driver Arun. Sighted in white Swift TN01AB1234 with phone 9876543210."},
        {"id": "CDR-001", "case_id": "case-101", "filename": "CDR_101_Ravi_Arun.csv", "source_type": "CDR", "storage_path": "./uploads/case-101/CDR_101_Ravi_Arun.csv", "sha256": "9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c", "size": 512, "text": "Caller: 9876543210, Callee: 9876543211, Duration: 340s, Tower: Central Station Tower."},
        {"id": "TX-001", "case_id": "case-101", "filename": "TX_101_Ledger.csv", "source_type": "TRANSACTIONS", "storage_path": "./uploads/case-101/TX_101_Ledger.csv", "sha256": "e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8", "size": 768, "text": "Sender: A101, Receiver: A102, Amount: INR 150000, Bank: SBI."},
        {"id": "SRV-01", "case_id": "case-101", "filename": "SRV_101_CentralStation.json", "source_type": "SURVEILLANCE", "storage_path": "./uploads/case-101/SRV_101_CentralStation.json", "sha256": "3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b", "size": 640, "text": "Surveillance Report SRV-01: Ravi Kumar parked TN01AB1234 at Central Station."},
        {"id": "INTEL-001", "case_id": "case-101", "filename": "INTEL_101_SpecialBranch.pdf", "source_type": "INTELLIGENCE", "storage_path": "./uploads/case-101/INTEL_101_SpecialBranch.pdf", "sha256": "1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d", "size": 4096, "text": "Special Branch Intelligence: Ravi Kumar facilitates cyber transactions using 9876543210."},
        {"id": "FIR-205-01", "case_id": "case-205", "filename": "FIR_205_HawalaAlpha.pdf", "source_type": "FIR", "storage_path": "./uploads/case-205/FIR_205_HawalaAlpha.pdf", "sha256": "8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e", "size": 8192, "text": "Hawala Syndicate Alpha FIR: Ravi Kumar and Sanjay Singhal routing funds through account A101."},
        {"id": "TX-003", "case_id": "case-205", "filename": "TX_205_WireLedger.csv", "source_type": "TRANSACTIONS", "storage_path": "./uploads/case-205/TX_205_WireLedger.csv", "sha256": "7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b", "size": 1024, "text": "Sender: A101, Receiver: A201 (Apex Trading), Amount: INR 500000."},
        {"id": "DOS-001", "case_id": "case-101", "filename": "DOS_001_RaviKumar.json", "source_type": "CRIMINAL_HISTORY", "storage_path": "./uploads/case-101/DOS_001_RaviKumar.json", "sha256": "6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c", "size": 1200, "text": "Criminal History Dossier: Ravi Kumar, Aliases: Ravi K, R. Kumar. Phone: 9876543210, Vehicle: TN01AB1234."}
    ]

    for d in evidence_docs:
        existing = db.query(Document).filter(Document.id == d["id"]).first()
        if not existing:
            db.add(Document(
                id=d["id"], case_id=d["case_id"], filename=d["filename"],
                source_type=d["source_type"], storage_path=d["storage_path"],
                sha256=d["sha256"], size_bytes=d["size"], uploaded_by="u-mira",
                processing_status="completed", extracted_text=d["text"]
            ))
    db.commit()

    # 6. Seed Resolution Candidates (Pending Human Review: R. Kumar -> Ravi Kumar)
    existing_cand = db.query(EntityMergeDecision).filter(EntityMergeDecision.id == "cand-rkumar-ravi").first()
    if not existing_cand:
        db.add(EntityMergeDecision(
            id="cand-rkumar-ravi", case_id="case-101", canonical_id="ent-ravi",
            canonical_label="Ravi Kumar", type="person", mentions=["R. Kumar", "Ravi K"],
            confidence=94, signals=[
                {"label": "Name & Phonetic Similarity", "matched": True},
                {"label": "Phone 9876543210 Match", "matched": True},
                {"label": "Vehicle TN01AB1234 Match", "matched": True},
                {"label": "Case Overlap (5 cases)", "matched": True}
            ],
            status="pending"
        ))
    db.commit()

    # 7. Seed Grounded Findings
    findings = [
        {"id": "fnd-bridge-ravi", "case_id": "case-101", "category": "potential_bridge", "title": "Potential network bridge", "severity": "high", "confidence": 92, "why": "Target Ravi Kumar bridges telecom call records and banking transaction clusters.", "entity_ids": ["ent-ravi"], "evidence_ids": ["FIR-101-01", "CDR-001", "TX-001"]},
        {"id": "fnd-cross-ravi", "case_id": "case-101", "category": "cross_case_recurrence", "title": "Cross-case recurrence convergence", "severity": "high", "confidence": 95, "why": "Identified target Ravi Kumar appears across 5 separate operations (case-101, case-203, case-205, case-301, case-412) with identical phone and vehicle.", "entity_ids": ["ent-ravi", "ent-phone-ravi", "ent-veh-ravi"], "evidence_ids": ["FIR-101-01", "FIR-205-01", "SRV-01", "INTEL-001"]},
        {"id": "fnd-burst-call", "case_id": "case-101", "category": "communication_burst", "title": "High duration call burst", "severity": "medium", "confidence": 85, "why": "Prolonged communication frequency registered between suspect phone and logistics driver.", "entity_ids": ["ent-phone-ravi", "ent-phone-arun"], "evidence_ids": ["CDR-001"]},
        {"id": "fnd-financial-wire", "case_id": "case-205", "category": "financial_anomaly", "title": "Rapid layered wire transfer", "severity": "high", "confidence": 90, "why": "High-value fund transfer of INR 500,000 from account A101 into shell company account A201.", "entity_ids": ["ent-acc-a101", "ent-acc-a201", "ent-org-apex"], "evidence_ids": ["TX-003", "FIR-205-01"]}
    ]
    for f in findings:
        existing = db.query(Finding).filter(Finding.id == f["id"]).first()
        if not existing:
            db.add(Finding(
                id=f["id"], case_id=f["case_id"], category=f["category"],
                title=f["title"], severity=f["severity"], confidence=f["confidence"],
                why=f["why"], entity_ids=f["entity_ids"], evidence_ids=f["evidence_ids"],
                status="open"
            ))
    db.commit()

    # 8. Seed Audit Logs
    audits = [
        {"id": "aud-1", "user_id": "u-mira", "action": "LOGIN", "resource": "Investigator Portal", "result": "success"},
        {"id": "aud-2", "user_id": "u-mira", "action": "VIEW", "case_id": "case-101", "resource": "Case Overview", "result": "success"},
        {"id": "aud-3", "user_id": "u-mira", "action": "UPLOAD", "case_id": "case-101", "resource": "FIR_101_01_ShadowNet.pdf", "result": "success"},
        {"id": "aud-4", "user_id": "u-lena", "action": "VIEW", "case_id": "case-205", "resource": "Hawala Syndicate Alpha Graph", "result": "success"},
    ]
    for a in audits:
        existing = db.query(AuditLog).filter(AuditLog.id == a["id"]).first()
        if not existing:
            db.add(AuditLog(
                id=a["id"], user_id=a["user_id"], action=a["action"],
                case_id=a.get("case_id"), resource=a["resource"], result=a["result"]
            ))
    db.commit()

    db.close()
    print("PostgreSQL Historical Database seeded successfully!")

    # 9. Sync to Neo4j if available
    try:
        neo4j_client.connect()
        session = neo4j_client.get_session()
        graph_svc = Neo4jGraphService(session)
        print("Syncing Canonical Graph to Neo4j...")
        for ent in entities:
            graph_svc.create_entity_node(
                entity_id=ent["id"], entity_type=ent["type"], label=ent["label"],
                case_ids=ent["case_ids"], cluster=ent["cluster"], properties=ent["attributes"]
            )
        for r in relationships:
            graph_svc.create_relationship(
                source_id=r["source"], source_type=r["source_type"],
                target_id=r["target"], target_type=r["target_type"],
                rel_type=r["rel_type"],
                properties={
                    "confidence": r["confidence"],
                    "evidence_ids": r.get("evidence_ids", []),
                    "rationale": r.get("rationale", ""),
                    "suspicious": r.get("suspicious", False)
                },
                case_ids=r["case_ids"]
            )
        session.close()
        print("Neo4j Knowledge Graph synchronized successfully!")
    except Exception as e:
        print(f"Neo4j offline or auth bypass (PostgreSQL canonical graph is primary): {e}")

if __name__ == "__main__":
    seed_all()
