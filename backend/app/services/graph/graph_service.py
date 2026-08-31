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
    "CALLS", "CALLED", "CONTACTED", "COMMUNICATED_WITH", "TRANSFERS", "TRANSFERRED_TO",
    "OWNS", "USES", "MENTIONED_IN", "SEEN_AT", "LOCATED_AT", "VISITED", "WORKS_FOR",
    "CO_OCCURS", "ASSOCIATED_WITH", "KNOWS", "CONNECTED_TO", "PART_OF_CASE", "INVOLVED_IN",
    "SENT_TO", "RECEIVED_FROM", "APPEARED_IN", "SUPPORTED_BY", "RELATED_TO", "LINKED_TO"
}

class Neo4jGraphService:
    def __init__(self, session: Session = None, db = None):
        self.session = session
        self.db = db

    def clear_db(self):
        """Clears all nodes and relationships."""
        if self.session:
            try:
                self.session.run("MATCH (n) DETACH DELETE n")
            except Exception as e:
                print(f"Neo4j clear error: {e}")

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

    def sync_postgres_to_neo4j(self) -> Dict[str, Any]:
        """
        Safe administrative graph sync operation.
        Reads canonical entities and relationships from PostgreSQL and MERGEs them into Neo4j.
        Preserves evidence references, timestamps, and case scopes without destroying data.
        """
        if not self.session or not self.db:
            return {"status": "skipped", "reason": "Neo4j or PostgreSQL session unavailable."}

        from app.models.models import CanonicalEntity, EntityRelationship
        entities = self.db.query(CanonicalEntity).all()
        relationships = self.db.query(EntityRelationship).all()

        nodes_synced = 0
        rels_synced = 0

        for ent in entities:
            self.create_entity_node(
                entity_id=ent.id,
                entity_type=ent.type,
                label=ent.label,
                case_ids=ent.case_ids or [],
                cluster=ent.cluster or "default",
                properties=ent.attributes or {}
            )
            nodes_synced += 1

        for rel in relationships:
            self.create_relationship(
                source_id=rel.source_id,
                source_type=rel.source_type,
                target_id=rel.target_id,
                target_type=rel.target_type,
                rel_type=rel.rel_type,
                properties={
                    "confidence": rel.confidence,
                    "evidence_ids": rel.evidence_ids or [],
                    "source": rel.source or "unknown",
                    "timestamp": rel.timestamp or "",
                    "time_from": rel.time_from or "",
                    "time_to": rel.time_to or "",
                    "created_by_pipeline": rel.created_by_pipeline or "sync",
                    "occurrences": rel.occurrences or 1,
                    "suspicious": rel.suspicious or False,
                    "rationale": rel.rationale or ""
                },
                case_ids=rel.case_ids or []
            )
            rels_synced += 1

        return {
            "status": "success",
            "nodes_synced": nodes_synced,
            "rels_synced": rels_synced,
            "pg_entities": len(entities),
            "pg_relationships": len(relationships)
        }

    def create_relationship(self, source_id: str, source_type: str, target_id: str, target_type: str, rel_type: str, properties: Dict[str, Any], case_ids: List[str] = None):
        """Creates a relationship with provenance properties in Neo4j and PostgreSQL."""
        rel_type = rel_type.upper()
        if rel_type not in ALLOWED_RELATIONSHIPS:
            raise ValueError(f"Invalid relationship type: {rel_type}")
            
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

        # 1. Sync to Neo4j if session is available
        if self.session:
            try:
                src_label = TYPE_TO_LABEL.get(source_type.lower(), "Person")
                tgt_label = TYPE_TO_LABEL.get(target_type.lower(), "Person")
                query = f"""
                MATCH (s:{src_label} {{id: $src_id}})
                MATCH (t:{tgt_label} {{id: $tgt_id}})
                MERGE (s)-[r:{rel_type}]->(t)
                SET r += $props
                """
                self.session.run(query, src_id=source_id, tgt_id=target_id, props=props)
            except Exception as e:
                print(f"Neo4j relationship insert error: {e}")

        # 2. Sync to PostgreSQL if db session is available
        if self.db:
            try:
                from app.models.models import EntityRelationship
                rel_id = f"rel-{source_id}-{target_id}-{rel_type}".lower()
                existing_rel = self.db.query(EntityRelationship).filter(EntityRelationship.id == rel_id).first()
                case_list = case_ids or properties.get("case_ids", [])
                if existing_rel:
                    existing_rel.confidence = props["confidence"]
                    existing_rel.evidence_ids = props["evidence_ids"]
                    existing_rel.source = props["source"]
                    existing_rel.timestamp = props["timestamp"]
                    existing_rel.time_from = props["time_from"]
                    existing_rel.time_to = props["time_to"]
                    existing_rel.created_by_pipeline = props["created_by_pipeline"]
                    existing_rel.occurrences = props["occurrences"]
                    existing_rel.suspicious = props["suspicious"]
                    existing_rel.rationale = props["rationale"]
                    for cid in case_list:
                        if cid not in existing_rel.case_ids:
                            existing_rel.case_ids = existing_rel.case_ids + [cid]
                else:
                    new_rel = EntityRelationship(
                        id=rel_id,
                        source_id=source_id,
                        source_type=source_type.lower(),
                        target_id=target_id,
                        target_type=target_type.lower(),
                        rel_type=rel_type,
                        case_ids=case_list,
                        confidence=props["confidence"],
                        evidence_ids=props["evidence_ids"],
                        source=props["source"],
                        timestamp=props["timestamp"],
                        time_from=props["time_from"],
                        time_to=props["time_to"],
                        created_by_pipeline=props["created_by_pipeline"],
                        occurrences=props["occurrences"],
                        suspicious=props["suspicious"],
                        rationale=props["rationale"]
                    )
                    self.db.add(new_rel)
                self.db.commit()
            except Exception as e:
                print(f"PostgreSQL relationship insert error: {e}")
                self.db.rollback()

    def get_subgraph(self, case_id: str, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Gets focused subgraph for a case from Neo4j, or from PostgreSQL canonical entities/relationships if Neo4j is offline."""
        filters = filters or {}
        min_confidence = int(filters.get("min_confidence", 0))
        limit = int(filters.get("limit", 100))
        selected_entity = filters.get("selected_entity")
        entity_type_filter = filters.get("entity_type")
        rel_type_filter = filters.get("relationship_type")
        suspicious_only = filters.get("suspicious_only", False)

        if self.session:
            try:
                nodes_dict = {}
                edges_list = []
                
                if selected_entity:
                    query = """
                    MATCH (n {id: $entity_id})
                    OPTIONAL MATCH (n)-[r]-(m)
                    WHERE ($min_conf IS NULL OR r.confidence >= $min_conf)
                    AND ($case_id IS NULL OR $case_id IN n.case_ids OR $case_id IN m.case_ids)
                    RETURN n, r, m LIMIT $limit
                    """
                    result = self.session.run(query, entity_id=selected_entity, min_conf=min_confidence, case_id=case_id, limit=limit)
                else:
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
                        nodes_dict[n_node["id"]] = {
                            "id": n_node["id"],
                            "type": n_node.get("type", "person"),
                            "label": n_node.get("label", n_node["id"]),
                            "caseIds": n_node.get("case_ids", []),
                            "cluster": n_node.get("cluster", "default"),
                            "attributes": {k: v for k, v in n_node.items() if k not in ["id", "type", "label", "case_ids", "cluster"]}
                        }
                    if m_node:
                        nodes_dict[m_node["id"]] = {
                            "id": m_node["id"],
                            "type": m_node.get("type", "person"),
                            "label": m_node.get("label", m_node["id"]),
                            "caseIds": m_node.get("case_ids", []),
                            "cluster": m_node.get("cluster", "default"),
                            "attributes": {k: v for k, v in m_node.items() if k not in ["id", "type", "label", "case_ids", "cluster"]}
                        }
                    if r_rel and n_node and m_node:
                        edges_list.append({
                            "id": f"e-{n_node['id']}-{m_node['id']}-{r_rel.type}",
                            "source": n_node["id"],
                            "target": m_node["id"],
                            "type": r_rel.type,
                            "confidence": r_rel.get("confidence", 50),
                            "occurrences": r_rel.get("occurrences", 1),
                            "timeframe": {"from": r_rel.get("time_from", ""), "to": r_rel.get("time_to", "")},
                            "evidenceIds": r_rel.get("evidence_ids", []),
                            "provenanceSource": r_rel.get("source", "unknown"),
                            "createdByPipeline": r_rel.get("created_by_pipeline", "manual"),
                            "suspicious": r_rel.get("suspicious", False),
                            "rationale": r_rel.get("rationale", "")
                        })

                if nodes_dict:
                    return {"nodes": list(nodes_dict.values()), "edges": edges_list, "graphSource": "neo4j"}
            except Exception as e:
                print(f"Neo4j subgraph error: {e}")

        # Fallback only exposes relationships that were genuinely persisted in PostgreSQL.
        if self.db:
            from app.models.models import CanonicalEntity, EntityRelationship
            ents = self.db.query(CanonicalEntity).all()
            nodes = []
            for ent in ents:
                if not case_id or case_id in ent.case_ids:
                    nodes.append({
                        "id": ent.id,
                        "type": ent.type,
                        "label": ent.label,
                        "subtitle": ent.subtitle,
                        "caseIds": ent.case_ids,
                        "aliases": ent.aliases,
                        "relevance": ent.relevance,
                        "cluster": ent.cluster,
                        "attributes": ent.attributes or {},
                        "x": ent.x,
                        "y": ent.y
                    })

            rels = self.db.query(EntityRelationship).all()
            edges = []
            for r in rels:
                if not case_id or case_id in r.case_ids:
                    if r.confidence >= min_confidence and (not suspicious_only or r.suspicious):
                        edges.append({
                            "id": r.id,
                            "source": r.source_id,
                            "target": r.target_id,
                            "type": r.rel_type,
                            "confidence": r.confidence,
                            "occurrences": r.occurrences,
                            "timeframe": {"from": r.time_from or "", "to": r.time_to or ""},
                            "evidenceIds": r.evidence_ids or [],
                            "provenanceSource": r.source or "unknown",
                            "createdByPipeline": r.created_by_pipeline,
                            "suspicious": r.suspicious,
                            "rationale": r.rationale or ""
                        })
            graph_source = "postgresql_canonical_fallback" if edges else "none"
            return {"nodes": nodes if edges else [], "edges": edges, "graphSource": graph_source}

        return {"nodes": [], "edges": [], "graphSource": "none"}

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
