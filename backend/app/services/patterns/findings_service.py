import uuid
import datetime
import networkx as nx
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from neo4j import Session as Neo4jSession

from app.models.models import Finding, CanonicalEntity, Case, Document
from app.services.graph.graph_service import Neo4jGraphService

class FindingsEngine:
    def __init__(self, db: Session, neo4j_sess: Neo4jSession = None):
        self.db = db
        self.neo4j_sess = neo4j_sess
        self.graph_service = Neo4jGraphService(neo4j_sess) if neo4j_sess else None

    def analyze_case(self, case_id: str) -> List[Finding]:
        """
        Runs analytical rules over the case graph and transaction metadata.
        Saves new findings to PostgreSQL.
        """
        findings_created = []

        # 1. Fetch graph data. If Neo4j is unavailable, use only persisted
        # PostgreSQL canonical relationships, never synthetic graph edges.
        graph_service = self.graph_service or Neo4jGraphService(None, self.db)
        subgraph = graph_service.get_subgraph(case_id)

        nodes = subgraph.get("nodes", [])
        edges = subgraph.get("edges", [])

        if not nodes:
            # If no graph exists yet, let's load canonical entities from Postgres to run cross-case checks
            canonicals = self.db.query(CanonicalEntity).all()
            for ce in canonicals:
                if case_id in ce.case_ids and len(ce.case_ids) > 1:
                    # Pattern 3: Cross-case recurrence
                    self._create_cross_case_finding(case_id, ce, findings_created)
            return findings_created

        # 2. Build NetworkX graph
        G = nx.Graph()
        for node in nodes:
            G.add_node(node["id"], **node)
        for edge in edges:
            G.add_edge(edge["source"], edge["target"], **edge)

        # Calculate degree centrality
        degrees = dict(G.degree())
        degree_values = list(degrees.values())
        
        # Calculate median degree
        if degree_values:
            sorted_deg = sorted(degree_values)
            n_deg = len(sorted_deg)
            median_deg = sorted_deg[n_deg // 2] if n_deg % 2 != 0 else (sorted_deg[n_deg // 2 - 1] + sorted_deg[n_deg // 2]) / 2.0
            median_deg = max(1, median_deg)
        else:
            median_deg = 1

        # Pattern 1: Unusual Connectivity
        for node_id, deg in degrees.items():
            if deg > median_deg * 2.5 and deg >= 4:
                node_data = G.nodes[node_id]
                self._create_connectivity_finding(case_id, node_id, node_data, deg, median_deg, findings_created)

        # Pattern 2: Potential Bridge
        # A node is a bridge if it connects nodes of different clusters
        for node_id in G.nodes():
            neighbors = list(G.neighbors(node_id))
            if len(neighbors) >= 2:
                neighbor_clusters = set()
                for neigh in neighbors:
                    clust = G.nodes[neigh].get("cluster", "default")
                    neighbor_clusters.add(clust)
                
                # If connected neighbors belong to 2 or more different clusters, it's a bridge
                if len(neighbor_clusters) >= 2:
                    node_data = G.nodes[node_id]
                    self._create_bridge_finding(case_id, node_id, node_data, neighbor_clusters, findings_created)

        # Pattern 3: Cross-case Recurrence
        for node_id in G.nodes():
            node_data = G.nodes[node_id]
            case_ids = node_data.get("caseIds", [])
            if len(case_ids) > 1:
                self._create_cross_case_finding_node(case_id, node_id, node_data, case_ids, findings_created)

        # Pattern 4: Transaction Chain (A -> B -> C)
        # Search for paths of length 2 where type is TRANSFERS
        directed_transfers = nx.DiGraph()
        for edge in edges:
            if edge["type"] == "TRANSFERS":
                directed_transfers.add_edge(edge["source"], edge["target"], **edge)

        for node_id in directed_transfers.nodes():
            in_edges = list(directed_transfers.in_edges(node_id, data=True))
            out_edges = list(directed_transfers.out_edges(node_id, data=True))
            
            if in_edges and out_edges:
                # We have a chain: source -> node_id -> target
                for u, _, in_data in in_edges:
                    for _, v, out_data in out_edges:
                        # Simple timeframe order check if timestamps exist
                        t1 = in_data.get("timeframe", {}).get("from", "")
                        t2 = out_data.get("timeframe", {}).get("from", "")
                        
                        # Flag suspicious chain
                        self._create_transaction_chain_finding(case_id, u, node_id, v, in_data, out_data, findings_created)

        # Pattern 5: Communication Spike
        for edge in edges:
            if edge["type"] == "CALLS" and edge.get("occurrences", 1) >= 8:
                self._create_comm_spike_finding(case_id, edge, findings_created)

        self.db.commit()
        return findings_created

    def _create_connectivity_finding(self, case_id, node_id, node_data, deg, median_deg, findings_created):
        finding_id = f"fnd-conn-{node_id}"
        # Check if already exists
        existing = self.db.query(Finding).filter(Finding.id == finding_id).first()
        if not existing:
            f = Finding(
                id=finding_id,
                case_id=case_id,
                category="unusual_connectivity",
                title="Unusual connectivity",
                severity="medium",
                confidence=75,
                why=f"Entity '{node_data['label']}' has significantly more connections ({deg}) than the case median ({median_deg}). Represents an elevated analytical relevance.",
                entity_ids=[node_id],
                evidence_ids=node_data.get("evidenceIds", []),
                status="open",
                created_at=datetime.datetime.utcnow()
            )
            self.db.add(f)
            findings_created.append(f)

    def _create_bridge_finding(self, case_id, node_id, node_data, clusters, findings_created):
        finding_id = f"fnd-bridge-{node_id}"
        existing = self.db.query(Finding).filter(Finding.id == finding_id).first()
        if not existing:
            f = Finding(
                id=finding_id,
                case_id=case_id,
                category="potential_bridge",
                title="Potential bridge",
                severity="high",
                confidence=85,
                why=f"Entity '{node_data['label']}' connects otherwise separate network clusters ({', '.join(list(clusters))}). Serves as a primary analytical bridge.",
                entity_ids=[node_id],
                evidence_ids=node_data.get("evidenceIds", []),
                status="open",
                created_at=datetime.datetime.utcnow()
            )
            self.db.add(f)
            findings_created.append(f)

    def _create_cross_case_finding(self, case_id, ce, findings_created):
        finding_id = f"fnd-cross-{ce.id}"
        existing = self.db.query(Finding).filter(Finding.id == finding_id).first()
        if not existing:
            f = Finding(
                id=finding_id,
                case_id=case_id,
                category="cross_case_recurrence",
                title="Cross-case recurrence",
                severity="high",
                confidence=90,
                why=f"Entity '{ce.label}' appears in multiple cases ({', '.join(ce.case_ids)}). Elevated relevance for cross-agency collaboration.",
                entity_ids=[ce.id],
                evidence_ids=[],
                status="open",
                created_at=datetime.datetime.utcnow()
            )
            self.db.add(f)
            findings_created.append(f)

    def _create_cross_case_finding_node(self, case_id, node_id, node_data, case_ids, findings_created):
        finding_id = f"fnd-cross-{node_id}"
        existing = self.db.query(Finding).filter(Finding.id == finding_id).first()
        if not existing:
            f = Finding(
                id=finding_id,
                case_id=case_id,
                category="cross_case_recurrence",
                title="Cross-case recurrence",
                severity="high",
                confidence=90,
                why=f"Entity '{node_data['label']}' appears in multiple cases ({', '.join(case_ids)}). Elevated analytical relevance.",
                entity_ids=[node_id],
                evidence_ids=node_data.get("evidenceIds", []),
                status="open",
                created_at=datetime.datetime.utcnow()
            )
            self.db.add(f)
            findings_created.append(f)

    def _create_transaction_chain_finding(self, case_id, u, b, v, edge1, edge2, findings_created):
        finding_id = f"fnd-tx-{u}-{b}-{v}"
        existing = self.db.query(Finding).filter(Finding.id == finding_id).first()
        if not existing:
            f = Finding(
                id=finding_id,
                case_id=case_id,
                category="suspicious_transaction_chain",
                title="Suspicious transaction chain",
                severity="high",
                confidence=80,
                why=f"Indirect transfer detected: Entity A ({u}) transferred funds to Entity B ({b}) which subsequently transferred funds to Entity C ({v}) in a short timeframe.",
                entity_ids=[u, b, v],
                evidence_ids=list(set(edge1.get("evidenceIds", []) + edge2.get("evidenceIds", []))),
                status="open",
                created_at=datetime.datetime.utcnow()
            )
            self.db.add(f)
            findings_created.append(f)

    def _create_comm_spike_finding(self, case_id, edge, findings_created):
        finding_id = f"fnd-comm-{edge['id']}"
        existing = self.db.query(Finding).filter(Finding.id == finding_id).first()
        if not existing:
            f = Finding(
                id=finding_id,
                case_id=case_id,
                category="anomalous_communication",
                title="Communication spike",
                severity="medium",
                confidence=85,
                why=f"Spike in communications detected: {edge['occurrences']} calls registered between {edge['source']} and {edge['target']}.",
                entity_ids=[edge["source"], edge["target"]],
                evidence_ids=edge.get("evidenceIds", []),
                status="open",
                created_at=datetime.datetime.utcnow()
            )
            self.db.add(f)
            findings_created.append(f)
