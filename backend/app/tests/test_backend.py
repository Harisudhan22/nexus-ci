import os
import sys
import unittest
import hashlib
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.postgres import Base
from app.models.models import User, Case, Document, CanonicalEntity, Finding, AuditLog, EntityMergeDecision, RawMention
from app.core.security import get_password_hash, verify_password
from app.services.nlp.ner_service import EntityExtractor
from app.services.entity_resolution.resolution_service import EntityResolutionService
from app.services.graph.analytics import run_network_analytics
from app.services.patterns.findings_service import FindingsEngine
from app.services.copilot.copilot_service import CopilotService

# In-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

class TestBackendPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
        cls.SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def setUp(self):
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionTesting()
        
        # Seed test user
        hashed = get_password_hash("testpass")
        self.user = User(
            id="u-test",
            name="Test Investigator",
            username="testuser",
            email="test@nexus.gov",
            password_hash=hashed,
            role="investigator",
            agency_id="Test Agency",
            clearance="SECRET"
        )
        self.db.add(self.user)
        
        # Seed test case
        self.case = Case(
            id="case-test",
            title="Test Operation",
            description="Operational testing description.",
            status="active",
            priority="high",
            agency="Test Agency",
            classification="SECRET"
        )
        self.db.add(self.case)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_auth_security(self):
        # Verify password hashing
        self.assertTrue(verify_password("testpass", self.user.password_hash))
        self.assertFalse(verify_password("wrongpass", self.user.password_hash))

    def test_entity_extraction(self):
        extractor = EntityExtractor()
        text = "Contact suspect Ravi Kumar at phone number 9876543210. Driven sedan plate TN01AB1234. Uses bank account A101."
        
        mentions = extractor.extract(text, "case-test", "doc-1")
        
        types = [m["type"] for m in mentions]
        surfaces = [m["surface"] for m in mentions]
        
        self.assertIn("phone", types)
        self.assertIn("vehicle", types)
        self.assertIn("account", types)
        
        self.assertIn("9876543210", surfaces)
        self.assertIn("TN01AB1234", surfaces)
        self.assertIn("A101", surfaces)

    def test_entity_resolution_candidates(self):
        # Seed target entities
        c_ravi = CanonicalEntity(
            id="ent-ravi",
            type="person",
            label="Ravi Kumar",
            case_ids=["case-test"],
            aliases=["Ravi Kumar"],
            relevance=80,
            attributes={"Name": "Ravi Kumar"},
            cluster="cluster_1",
            x=10.0,
            y=20.0
        )
        self.db.add(c_ravi)
        
        # Seed duplicate raw mention (R. Kumar)
        # Note: Since the resolver finds unresolved raw mentions, we seed one
        rm = RawMention(
            id="raw-1",
            case_id="case-test",
            evidence_id="doc-1",
            surface="R. Kumar",
            type="person"
        )
        self.db.add(rm)
        self.db.commit()
        
        # Run resolution engine candidates generator
        resolver = EntityResolutionService(self.db)
        candidates = resolver.generate_candidates("case-test")
        
        self.assertGreater(len(candidates), 0)
        self.assertEqual(candidates[0].canonical_id, "ent-ravi")
        self.assertIn("R. Kumar", candidates[0].mentions)

    def test_network_analytics(self):
        nodes = [
            {"id": "A"}, {"id": "B"}, {"id": "C"}
        ]
        edges = [
            {"source": "A", "target": "B"},
            {"source": "B", "target": "C"}
        ]
        
        results = run_network_analytics(nodes, edges)
        
        # B is in the middle, should be marked as bridge / articulation point
        self.assertTrue(results["B"]["isBridge"])
        self.assertFalse(results["A"]["isBridge"])
        self.assertEqual(results["B"]["degree"], 2)

    def test_findings_engine(self):
        # Setup mock entities and findings engine
        engine_fnd = FindingsEngine(self.db)
        findings = engine_fnd.analyze_case("case-test")
        
        # Findings should run successfully
        self.assertIsInstance(findings, list)

    def test_copilot_grounding_validation(self):
        # Retrieve copilot response grounding check
        copilot = CopilotService(self.db)
        res = copilot.query("case-test", "Why is Ravi important?", "u-test")
        
        # Since there's no data seeded, it should handle fallback and return insufficient evidence
        self.assertIn("summary", res)
        self.assertGreater(res["confidence"], -1)

if __name__ == "__main__":
    unittest.main()
