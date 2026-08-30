import os
import sys
import unittest
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.postgres import Base
from app.models.models import (
    User, Case, Document, CanonicalEntity, EntityRelationship,
    Finding, AuditLog, SourceRecord, DocumentChunk, SourceJob
)
from app.core.security import get_password_hash
from app.services.analytics.graph_analytics import GraphAnalyticsService
from app.services.analytics.pattern_engine import SuspiciousPatternEngine
from app.services.rag.rag_service import RAGService
from app.services.copilot.copilot_service import CopilotService

TEST_DATABASE_URL = "sqlite:///:memory:"

class TestP1Platform(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
        cls.SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def setUp(self):
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionTesting()

        # Seed Users
        hashed = get_password_hash("testpass")
        self.admin = User(id="u-admin", name="Admin User", username="admin", email="admin@nexus.gov", password_hash=hashed, role="admin", agency_id="HQ", clearance="SECRET")
        self.db.add(self.admin)

        # Seed Cases
        self.case1 = Case(id="case-101", title="Shadow Net", description="Cyber ring", status="active", priority="high", agency="SCB", classification="SECRET", assigned_to="u-admin")
        self.case2 = Case(id="case-205", title="Hawala Ring", description="Financial ring", status="active", priority="critical", agency="FIU", classification="SECRET", assigned_to="u-admin")
        self.db.add_all([self.case1, self.case2])

        # Seed Entities
        self.ent_ravi = CanonicalEntity(
            id="ent-ravi", type="person", label="Ravi Kumar", subtitle="Target",
            case_ids=["case-101", "case-205"], aliases=["Ravi Kumar", "R. Kumar"],
            relevance=95, attributes={"Phone": "9876543210", "Plate": "TN01AB1234"}, cluster="cluster_1"
        )
        self.ent_phone = CanonicalEntity(
            id="ent-phone-1", type="phone", label="9876543210", subtitle="Device",
            case_ids=["case-101", "case-205"], aliases=["9876543210"], relevance=85,
            attributes={"Provider": "Jio"}, cluster="cluster_1"
        )
        self.ent_veh = CanonicalEntity(
            id="ent-veh-1", type="vehicle", label="TN01AB1234", subtitle="Sedan",
            case_ids=["case-101"], aliases=["TN01AB1234"], relevance=80,
            attributes={"Model": "Swift"}, cluster="cluster_1"
        )
        self.db.add_all([self.ent_ravi, self.ent_phone, self.ent_veh])

        # Seed Relationships
        self.rel1 = EntityRelationship(
            id="rel-ravi-phone", source_id="ent-ravi", source_type="person",
            target_id="ent-phone-1", target_type="phone", rel_type="OWNS",
            case_ids=["case-101", "case-205"], confidence=95, evidence_ids=["FIR-101"],
            occurrences=25, rationale="Phone registered to suspect Ravi Kumar."
        )
        self.rel2 = EntityRelationship(
            id="rel-ravi-veh", source_id="ent-ravi", source_type="person",
            target_id="ent-veh-1", target_type="vehicle", rel_type="USES",
            case_ids=["case-101"], confidence=90, evidence_ids=["FIR-101"],
            occurrences=5, rationale="Sedan driven by suspect."
        )
        self.db.add_all([self.rel1, self.rel2])

        # Seed Document
        self.doc1 = Document(
            id="FIR-101", case_id="case-101", filename="FIR_101.pdf",
            source_type="FIR", storage_path="./uploads/FIR_101.pdf",
            sha256="abc123sha256", size_bytes=2048, uploaded_by="u-admin",
            processing_status="completed", extracted_text="FIR-101: Suspect Ravi Kumar used phone number 9876543210 and white sedan TN01AB1234."
        )
        self.db.add(self.doc1)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_graph_analytics_centrality_and_communities(self):
        svc = GraphAnalyticsService(self.db)
        cent = svc.compute_centrality(case_id="case-101")
        self.assertIn("nodes", cent)
        self.assertGreater(len(cent["nodes"]), 0)

        comms = svc.compute_communities(case_id="case-101")
        self.assertIsInstance(comms, list)

        dna = svc.get_network_dna(case_id="case-101")
        self.assertGreater(dna["networkSize"], 0)

    def test_real_rag_chunking_and_retrieval(self):
        rag_svc = RAGService(self.db)
        chunks = rag_svc.chunk_document("FIR-101", "case-101", self.doc1.extracted_text, source_type="FIR")
        self.assertGreater(len(chunks), 0)

        # Critical RAG verification
        res = rag_svc.query_rag(question="Which phone is associated with Ravi Kumar?", case_id="case-101")
        self.assertGreater(res["matchCount"], 0)
        self.assertIn("FIR-101", res["sources"])
        self.assertIn("9876543210", res["retrievedChunks"][0]["textContent"])

    def test_suspicious_pattern_detection_and_priority(self):
        engine = SuspiciousPatternEngine(self.db)
        patterns = engine.detect_all_patterns(case_id="case-101")
        self.assertGreater(len(patterns), 0)

        priority = engine.calculate_investigation_priority(entity_id="ent-ravi", case_id="case-101")
        self.assertGreater(priority["priorityScore"], 50)
        self.assertIn("components", priority)

    def test_copilot_grounded_response(self):
        copilot = CopilotService(self.db)
        ans = copilot.query(case_id="case-101", question="Which previous cases are connected to Ravi Kumar?", user_id="u-admin")
        self.assertIn("summary", ans)
        self.assertIn("case-101", ans["summary"])
        self.assertIn("case-205", ans["summary"])

if __name__ == "__main__":
    unittest.main()
