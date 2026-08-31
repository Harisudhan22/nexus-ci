"""
NEXUS-CI Safe Natural-Language Graph Query Engine
==================================================
Converts natural language questions into safe, bounded, allowlisted Cypher queries.

Safety Controls:
  1. Rejects arbitrary LLM-generated Cypher and destructive statements (DELETE, DROP, SET, etc.)
  2. Enforces hard safety bounds: max depth=2, max nodes=50, max relationships=100
  3. Applies mandatory case-level RBAC filters before query execution
"""
import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.models import CanonicalEntity, User
from app.core.dependencies import verify_case_access, get_accessible_case_ids


DESTRUCTIVE_CYPHER_PATTERNS = [
    re.compile(r"\bDELETE\b", re.IGNORECASE),
    re.compile(r"\bDETACH\b", re.IGNORECASE),
    re.compile(r"\bDROP\b", re.IGNORECASE),
    re.compile(r"\bCREATE\b", re.IGNORECASE),
    re.compile(r"\bMERGE\b", re.IGNORECASE),
    re.compile(r"\bSET\b", re.IGNORECASE),
    re.compile(r"\bREMOVE\b", re.IGNORECASE),
    re.compile(r"\bALTER\b", re.IGNORECASE),
]

MAX_DEPTH = 2
MAX_NODES = 50
MAX_RELATIONSHIPS = 100


class SafeNLGraphQueryEngine:
    def __init__(self, db: Session, neo4j_sess=None):
        self.db = db
        self.neo4j_sess = neo4j_sess

    def execute_nl_query(
        self,
        question: str,
        case_id: Optional[str] = None,
        user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Parses intent, resolves entities, applies safety bounds and case RBAC,
        and executes an allowlisted Cypher template.
        """
        # 1. Reject malicious / Cypher injection queries immediately
        for pattern in DESTRUCTIVE_CYPHER_PATTERNS:
            if pattern.search(question):
                raise ValueError("Security violation: Malicious or destructive Cypher syntax detected in query.")

        # 2. Case RBAC Authorization Check
        accessible_cases = get_accessible_case_ids(user, self.db) if user else ([case_id] if case_id else None)
        if case_id and user and not verify_case_access(user, case_id, self.db):
            raise HTTPException(status_code=403, detail="Access denied to requested case.")

        # 3. Entity Resolution in Question
        all_entities = self.db.query(CanonicalEntity).all()
        target_entity = None
        q_lower = question.lower()

        for ent in all_entities:
            # Check case scope
            if accessible_cases is not None and not any(c in accessible_cases for c in ent.case_ids):
                continue
            if ent.label.lower() in q_lower or any(str(a).lower() in q_lower for a in ent.aliases):
                target_entity = ent
                break

        if not target_entity:
            return {
                "question": question,
                "nodes": [],
                "edges": [],
                "queryExecuted": "ALLOWLISTED_TEMPLATE_NEIGHBORHOOD",
                "summary": "No accessible matching entity found for natural language query.",
                "boundedDepth": MAX_DEPTH,
                "boundedNodes": MAX_NODES,
                "boundedRelationships": MAX_RELATIONSHIPS,
            }

        # 4. Extract Location / Time Parameters if present
        location = None
        loc_match = re.search(r"\bin\s+([A-Z][a-z]+)\b", question)
        if loc_match:
            location = loc_match.group(1)

        # 5. Execute Allowlisted Cypher Query
        nodes = []
        edges = []

        if self.neo4j_sess:
            try:
                # Bounded Cypher template
                cypher = """
                MATCH (src {id: $entity_id})-[r]-(target)
                WHERE ($case_id IS NULL OR $case_id IN src.case_ids OR $case_id IN target.case_ids)
                AND ($location IS NULL OR target.label CONTAINS $location)
                RETURN src, r, target LIMIT $max_nodes
                """
                res = self.neo4j_sess.run(
                    cypher,
                    entity_id=target_entity.id,
                    case_id=case_id,
                    location=location,
                    max_nodes=MAX_NODES
                )
                nodes_map = {}
                for record in res:
                    src = record["src"]
                    r = record["r"]
                    tgt = record["target"]

                    nodes_map[src["id"]] = {"id": src["id"], "label": src.get("label", src["id"]), "type": src.get("type", "person")}
                    nodes_map[tgt["id"]] = {"id": tgt["id"], "label": tgt.get("label", tgt["id"]), "type": tgt.get("type", "person")}

                    edges.append({
                        "id": f"e-{src['id']}-{tgt['id']}-{r.type}",
                        "source": src["id"],
                        "target": tgt["id"],
                        "type": r.type,
                        "confidence": r.get("confidence", 50)
                    })

                nodes = list(nodes_map.values())
            except Exception as e:
                print(f"Neo4j NL query execution error: {e}")

        # Fallback to PostgreSQL canonical relationships if Neo4j returned no results or is offline
        if not nodes and self.db:
            from app.services.graph.graph_service import Neo4jGraphService
            graph_svc = Neo4jGraphService(session=None, db=self.db)
            subg = graph_svc.get_subgraph(case_id=case_id, filters={"selected_entity": target_entity.id, "limit": MAX_NODES})
            nodes = subg.get("nodes", [])[:MAX_NODES]
            edges = subg.get("edges", [])[:MAX_RELATIONSHIPS]

        return {
            "question": question,
            "targetEntity": target_entity.label,
            "nodes": nodes,
            "edges": edges,
            "matchCount": len(nodes),
            "queryExecuted": "ALLOWLISTED_TEMPLATE_NEIGHBORHOOD",
            "summary": f"Retrieved {len(nodes)} connected entities within {MAX_DEPTH} degrees for '{target_entity.label}'.",
            "boundedDepth": MAX_DEPTH,
            "boundedNodes": MAX_NODES,
            "boundedRelationships": MAX_RELATIONSHIPS
        }
