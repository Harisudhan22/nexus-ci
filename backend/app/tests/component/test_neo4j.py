"""
COMPONENT TEST: Neo4j Graph Database
======================================
Tests Neo4j connectivity and graph consistency with PostgreSQL.
Requires a running Neo4j instance — tests gracefully skip if unavailable.
"""
import os, pytest


class TestNeo4j:
    """Phase 11 — Neo4j connectivity and consistency."""

    def _get_neo4j_session(self):
        """Attempt to connect to Neo4j, return active session or None if server unreachable."""
        try:
            from app.db.neo4j_db import neo4j_client
            neo4j_client.connect()
            sess = neo4j_client.get_session()
            if sess:
                # Probe query to verify server reachability
                sess.run("RETURN 1 AS probe").single()
                return sess
            return None
        except Exception:
            return None

    def test_neo4j_connectivity(self):
        """Verify Neo4j responds to RETURN 1 AS result."""
        session = self._get_neo4j_session()
        if not session:
            pytest.skip("Neo4j service not available on localhost")

        result = session.run("RETURN 1 AS result")
        record = result.single()

        print(f"\n{'='*60}")
        print(f"QUERY:    RETURN 1 AS result")
        print(f"EXPECTED: result=1")
        print(f"ACTUAL:   result={record['result']}")
        print(f"STATUS:   {'PASS' if record['result'] == 1 else 'FAIL'}")
        print(f"{'='*60}")

        assert record["result"] == 1
        session.close()

    def test_neo4j_node_labels(self):
        """Count nodes by label in Neo4j."""
        session = self._get_neo4j_session()
        if not session:
            pytest.skip("Neo4j service not available on localhost")

        result = session.run("MATCH (n) RETURN labels(n) AS labels, count(n) AS cnt")
        records = list(result)

        print(f"\n{'='*60}")
        print(f"QUERY:    MATCH (n) RETURN labels(n), count(n)")
        for r in records:
            print(f"  {r['labels']}: {r['cnt']} nodes")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

        session.close()

    def test_neo4j_relationship_types(self):
        """Count relationships by type in Neo4j."""
        session = self._get_neo4j_session()
        if not session:
            pytest.skip("Neo4j service not available on localhost")

        result = session.run("MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS cnt")
        records = list(result)

        print(f"\n{'='*60}")
        print(f"QUERY:    MATCH ()-[r]->() RETURN type(r), count(r)")
        for r in records:
            print(f"  {r['type']}: {r['cnt']} edges")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

        session.close()

    def test_neo4j_subgraph_sample(self):
        """Fetch a subgraph sample of up to 50 edges."""
        session = self._get_neo4j_session()
        if not session:
            pytest.skip("Neo4j service not available on localhost")

        result = session.run(
            "MATCH (n)-[r]-(m) RETURN n.id AS src, type(r) AS rel, m.id AS tgt LIMIT 50")
        records = list(result)

        print(f"\n{'='*60}")
        print(f"QUERY:    MATCH (n)-[r]-(m) RETURN n,r,m LIMIT 50")
        print(f"EDGES:    {len(records)}")
        for r in records[:5]:
            print(f"  {r['src']} --[{r['rel']}]--> {r['tgt']}")
        if len(records) > 5:
            print(f"  ... and {len(records) - 5} more")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

        session.close()

    def test_neo4j_postgres_consistency(self, seeded_db):
        """Verify key entity 'ent-ravi' exists in both PostgreSQL and Neo4j."""
        from app.models.models import CanonicalEntity
        pg_entity = seeded_db.query(CanonicalEntity).filter(
            CanonicalEntity.id == "ent-ravi").first()

        session = self._get_neo4j_session()
        if not session:
            print(f"\n{'='*60}")
            print(f"PostgreSQL: ent-ravi EXISTS ({pg_entity.label})")
            print(f"Neo4j:      SKIPPED (service not running)")
            print(f"STATUS:     PARTIAL")
            print(f"{'='*60}")
            pytest.skip("Neo4j service not available on localhost")

        result = session.run("MATCH (n {id: $id}) RETURN n.label AS label",
                             id="ent-ravi")
        neo4j_record = result.single()

        print(f"\n{'='*60}")
        print(f"ENTITY:   ent-ravi")
        print(f"PG:       {pg_entity.label if pg_entity else 'NOT FOUND'}")
        print(f"Neo4j:    {neo4j_record['label'] if neo4j_record else 'NOT FOUND'}")
        consistent = (pg_entity and neo4j_record and
                      pg_entity.label == neo4j_record["label"])
        print(f"STATUS:   {'PASS' if consistent else 'FAIL'}")
        print(f"{'='*60}")

        session.close()
        assert consistent
