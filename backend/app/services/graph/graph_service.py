import math
from typing import Dict, List, Any, Optional
from neo4j import Session
from app.db.neo4j_db import get_neo4j

# Map frontend entity types to Neo4j Node Labels
TYPE_TO_LABEL = {
    "person": "Person",
    "phone": "Phone",
    "vehicle": "Vehicle",
    "account": "Account",
    "location": "Location",
    "org": "Organization",
    "case": "Case",
    "document": "Document",
    "event": "Event"
}

LABEL_TO_TYPE = {v: k for k, v in TYPE_TO_LABEL.items()}

ALLOWED_RELATIONSHIPS = {
    "CALLS", "TRANSFERS", "OWNS", "MENTIONED_IN", "SEEN_AT",
    "CO_OCCURS", "ASSOCIATED_WITH", "VISITED", "LINKED_TO"
}

class Neo4jGraphService:
    def __init__(self, session: Session):
        self.session = session

    def clear_db(self):
        """Clears all nodes and relationships."""
        if not self.session:
            return
        self.session.run("MATCH (n) DETACH DELETE n")

    def create_entity_node(self, entity_id: str, entity_type: str, label: str, case_ids: List[str], cluster: str = None, properties: Dict[str, Any] = None):
        """Creates or updates a node representing an entity."""
        if not self.session:
            return
        node_label = TYPE_TO_LABEL.get(entity_type.lower(), "Person")
        props = {
            "id": entity_id,
            "label": label,
            "type": entity_type.lower(),
            "case_ids": case_ids,
            "cluster": cluster or "default",
            **(properties or {})
        }
        
        query = f"""
        MERGE (n:{node_label} {{id: $id}})
        SET n += $props
        """
        self.session.run(query, id=entity_id, props=props)

    def create_relationship(self, source_id: str, source_type: str, target_id: str, target_type: str, rel_type: str, properties: Dict[str, Any]):
        """Creates a relationship with provenance properties."""
        if not self.session:
            return
        
        # Validate relationship type
        rel_type = rel_type.upper()
        if rel_type not in ALLOWED_RELATIONSHIPS:
            raise ValueError(f"Invalid relationship type: {rel_type}")
            
        src_label = TYPE_TO_LABEL.get(source_type.lower(), "Person")
        tgt_label = TYPE_TO_LABEL.get(target_type.lower(), "Person")
        
        # Convert list of evidence IDs to string or let it pass if Neo4j supports list arrays
        evidence_ids = properties.get("evidence_ids", [])
        if not isinstance(evidence_ids, list):
            evidence_ids = [evidence_ids]
            
        props = {
            "confidence": int(properties.get("confidence", 50)),
            "evidence_ids": [str(x) for x in evidence_ids],
            "source": str(properties.get("source", "unknown")),
            "timestamp": str(properties.get("timestamp", "")),
            "time_from": str(properties.get("time_from", "")),
            "time_to": str(properties.get("time_to", "")),
            "created_by_pipeline": str(properties.get("created_by_pipeline", "manual")),
            "occurrences": int(properties.get("occurrences", 1)),
            "suspicious": bool(properties.get("suspicious", False)),
            "rationale": str(properties.get("rationale", "No rationale supplied."))
        }
        
        # Cypher parameterized query
        query = f"""
        MATCH (s:{src_label} {{id: $src_id}})
        MATCH (t:{tgt_label} {{id: $tgt_id}})
        MERGE (s)-[r:{rel_type}]->(t)
        SET r += $props
        """
        self.session.run(query, src_id=source_id, tgt_id=target_id, props=props)

    def get_subgraph(self, case_id: str, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Gets focused subgraph for a case."""
        if not self.session:
            # Return empty structure if Neo4j is offline in local dev fallback
            return {"nodes": [], "edges": []}
            
        filters = filters or {}
        min_confidence = int(filters.get("min_confidence", 0))
        limit = int(filters.get("limit", 100))
        selected_entity = filters.get("selected_entity")
        entity_type_filter = filters.get("entity_type")
        rel_type_filter = filters.get("relationship_type")
        suspicious_only = filters.get("suspicious_only", False)
        
        nodes_dict = {}
        edges_list = []
        
        # If an entity is selected, we focus on its neighborhood
        if selected_entity:
            # Query for the selected node and its immediate neighbors
            query = """
            MATCH (n {id: $entity_id})
            OPTIONAL MATCH (n)-[r]-(m)
            WHERE ($min_conf IS NULL OR r.confidence >= $min_conf)
            AND ($case_id IS NULL OR $case_id IN n.case_ids OR $case_id IN m.case_ids)
            RETURN n, r, m LIMIT $limit
            """
            result = self.session.run(query, entity_id=selected_entity, min_conf=min_confidence, case_id=case_id, limit=limit)
        else:
            # Query the whole subgraph matching filters
            query = """
            MATCH (n)-[r]->(m)
            WHERE ($case_id IS NULL OR ($case_id IN n.case_ids AND $case_id IN m.case_ids))
            AND ($min_conf IS NULL OR r.confidence >= $min_conf)
            AND ($suspicious IS FALSE OR r.suspicious = true)
            RETURN n, r, m LIMIT $limit
            """
            result = self.session.run(query, case_id=case_id, min_conf=min_confidence, suspicious=suspicious_only, limit=limit)
            
        for record in result:
            n_node = record.get("n")
            r_rel = record.get("r")
            m_node = record.get("m")
            
            if n_node:
                n_id = n_node["id"]
                # Apply type filter on node if specified
                node_type = n_node.get("type", "person")
                if not entity_type_filter or node_type == entity_type_filter:
                    nodes_dict[n_id] = {
                        "id": n_id,
                        "type": node_type,
                        "label": n_node.get("label", n_id),
                        "subtitle": n_node.get("subtitle"),
                        "caseIds": n_node.get("case_ids", []),
                        "aliases": n_node.get("aliases", []),
                        "relevance": int(n_node.get("relevance", 50)),
                        "cluster": n_node.get("cluster", "default"),
                        "attributes": dict(n_node.items()),
                        "x": float(n_node.get("x", 0.0)),
                        "y": float(n_node.get("y", 0.0))
                    }
                    
            if m_node:
                m_id = m_node["id"]
                node_type = m_node.get("type", "person")
                if not entity_type_filter or node_type == entity_type_filter:
                    nodes_dict[m_id] = {
                        "id": m_id,
                        "type": node_type,
                        "label": m_node.get("label", m_id),
                        "subtitle": m_node.get("subtitle"),
                        "caseIds": m_node.get("case_ids", []),
                        "aliases": m_node.get("aliases", []),
                        "relevance": int(m_node.get("relevance", 50)),
                        "cluster": m_node.get("cluster", "default"),
                        "attributes": dict(m_node.items()),
                        "x": float(m_node.get("x", 0.0)),
                        "y": float(m_node.get("y", 0.0))
                    }
                    
            if r_rel and n_node and m_node:
                r_type = r_rel.type
                if not rel_type_filter or r_type == rel_type_filter.upper():
                    edges_list.append({
                        "id": f"e-{n_node['id']}-{m_node['id']}-{r_type}",
                        "source": n_node["id"],
                        "target": m_node["id"],
                        "type": r_type,
                        "confidence": int(r_rel.get("confidence", 50)),
                        "occurrences": int(r_rel.get("occurrences", 1)),
                        "timeframe": {
                            "from": r_rel.get("time_from", ""),
                            "to": r_rel.get("time_to", "")
                        },
                        "evidenceIds": r_rel.get("evidence_ids", []),
                        "createdByPipeline": r_rel.get("created_by_pipeline", "manual"),
                        "suspicious": bool(r_rel.get("suspicious", False)),
                        "rationale": r_rel.get("rationale", "")
                    })
                    
        # Ensure selected entity node is in returned nodes even if it has no connections
        if selected_entity and selected_entity not in nodes_dict:
            single_result = self.session.run("MATCH (n {id: $id}) RETURN n", id=selected_entity)
            for rec in single_result:
                node = rec["n"]
                nodes_dict[selected_entity] = {
                    "id": selected_entity,
                    "type": node.get("type", "person"),
                    "label": node.get("label", selected_entity),
                    "subtitle": node.get("subtitle"),
                    "caseIds": node.get("case_ids", []),
                    "aliases": node.get("aliases", []),
                    "relevance": int(node.get("relevance", 50)),
                    "cluster": node.get("cluster", "default"),
                    "attributes": dict(node.items()),
                    "x": float(node.get("x", 0.0)),
                    "y": float(node.get("y", 0.0))
                }

        return {"nodes": list(nodes_dict.values()), "edges": edges_list}

    def get_path(self, from_id: str, to_id: str, mode: str = "shortest", case_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Finds a path between two entities in Neo4j.
        Supported modes: 'shortest' or 'strongest_evidence'.
        If no path exists, returns None.
        """
        if not self.session:
            return None
            
        # Modes mapping
        if mode == "strongest":
            # Dijkstra query to maximize confidence (cost = -log(confidence/100)) or 101 - confidence
            # Let's run a query that weights paths. In Neo4j GDS we could do dijkstra, but since GDS may not be installed,
            # we can run a cypher path query and calculate weights in Cypher or Python.
            # Let's query paths up to 5 hops, and calculate cost in Python to be robust.
            query = """
            MATCH p = (src {id: $from_id})-[:CALLS|TRANSFERS|OWNS|MENTIONED_IN|SEEN_AT|CO_OCCURS|ASSOCIATED_WITH|VISITED|LINKED_TO*1..5]-(tgt {id: $to_id})
            WHERE $case_id IS NULL OR ALL(rel IN relationships(p) WHERE $case_id IN rel.evidence_ids OR any(c_id in nodes(p) WHERE $case_id in c_id.case_ids))
            RETURN p
            """
            result = self.session.run(query, from_id=from_id, to_id=to_id, case_id=case_id)
            best_path = None
            best_cost = float("inf")
            for record in result:
                path = record["p"]
                # Calculate cost: sum(-log(confidence / 100))
                cost = 0
                for rel in path.relationships:
                    conf = rel.get("confidence", 50)
                    if conf <= 0:
                        conf = 1
                    cost += -math.log(conf / 100.0)
                if cost < best_cost:
                    best_cost = cost
                    best_path = path
                    
            if not best_path:
                return None
            return self._format_neo4j_path(best_path)
            
        else: # shortest path
            query = """
            MATCH p = shortestPath((src {id: $from_id})-[:CALLS|TRANSFERS|OWNS|MENTIONED_IN|SEEN_AT|CO_OCCURS|ASSOCIATED_WITH|VISITED|LINKED_TO*1..8]-(tgt {id: $to_id}))
            RETURN p
            """
            result = self.session.run(query, from_id=from_id, to_id=to_id)
            record = result.single()
            if not record or not record["p"]:
                return None
            return self._format_neo4j_path(record["p"])

    def _format_neo4j_path(self, path) -> Dict[str, Any]:
        node_ids = [n["id"] for n in path.nodes]
        edges = []
        for rel in path.relationships:
            edges.append({
                "id": f"e-{rel.start_node['id']}-{rel.end_node['id']}-{rel.type}",
                "source": rel.start_node["id"],
                "target": rel.end_node["id"],
                "type": rel.type,
                "confidence": int(rel.get("confidence", 50)),
                "occurrences": int(rel.get("occurrences", 1)),
                "timeframe": {
                    "from": rel.get("time_from", ""),
                    "to": rel.get("time_to", "")
                },
                "evidenceIds": rel.get("evidence_ids", []),
                "createdByPipeline": rel.get("created_by_pipeline", "manual"),
                "suspicious": bool(rel.get("suspicious", False)),
                "rationale": rel.get("rationale", "")
            })
        total_confidence = 0
        if edges:
            total_confidence = int(sum(e["confidence"] for e in edges) / len(edges))
            
        return {
            "nodeIds": node_ids,
            "edges": edges,
            "totalConfidence": total_confidence,
            "hops": len(edges)
        }
