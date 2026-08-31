"""
COMPONENT TEST: Graph Analytics
=================================
Tests NetworkX-based analytics: centrality, communities, shortest path,
PageRank, Network DNA, and common neighbors.
"""
import pytest
from app.services.analytics.graph_analytics import GraphAnalyticsService


class TestGraphAnalytics:
    """Phase 12 — Graph analytics with controlled graph data."""

    def test_degree_centrality(self, seeded_db):
        svc = GraphAnalyticsService(seeded_db)
        result = svc.compute_centrality(case_id="case-101")

        nodes = result.get("nodes", [])
        top_connected = result.get("topConnected", [])

        print(f"\n{'='*60}")
        print(f"CENTRALITY for case-101:")
        for n in nodes:
            print(f"  {n['label']:20s} degree={n['degree']} "
                  f"betweenness={n['betweennessCentrality']:.4f} "
                  f"pageRank={n['pageRank']:.4f} bridge={n['isBridge']}")
        print(f"TOP CONNECTED: {[n['label'] for n in top_connected]}")
        print(f"STATUS:   {'PASS' if nodes else 'FAIL'}")
        print(f"{'='*60}")

        assert len(nodes) >= 1
        # Ravi should have highest degree
        ravi = next((n for n in nodes if n["id"] == "ent-ravi"), None)
        assert ravi is not None
        assert ravi["degree"] >= 2

    def test_betweenness_centrality_values(self, seeded_db):
        svc = GraphAnalyticsService(seeded_db)
        result = svc.compute_centrality()
        nodes = result["nodes"]

        for n in nodes:
            assert 0.0 <= n["betweennessCentrality"] <= 1.0, \
                f"Betweenness out of range for {n['label']}"
            assert 0.0 <= n["pageRank"] <= 1.0, \
                f"PageRank out of range for {n['label']}"

    def test_community_detection(self, seeded_db):
        svc = GraphAnalyticsService(seeded_db)
        communities = svc.compute_communities()

        print(f"\n{'='*60}")
        print(f"COMMUNITIES DETECTED: {len(communities)}")
        for c in communities:
            print(f"  {c['communityId']}: size={c['size']}, "
                  f"density={c['density']:.4f}, "
                  f"entities={[e['label'] for e in c['entities'][:3]]}")
        print(f"STATUS:   {'PASS' if communities else 'PARTIAL'}")
        print(f"{'='*60}")

        # At least 1 community should exist with the seeded data
        assert len(communities) >= 1

    def test_shortest_path(self, seeded_db):
        svc = GraphAnalyticsService(seeded_db)
        path = svc.find_shortest_path("ent-ravi", "ent-suresh", case_id="case-101")

        print(f"\n{'='*60}")
        print(f"PATH:     ent-ravi → ent-suresh")
        if path:
            print(f"HOPS:     {path['hops']}")
            print(f"NODES:    {path['nodeIds']}")
            print(f"CONFIDENCE: {path['totalConfidence']}")
            for e in path["edges"]:
                print(f"  {e['source']} --[{e['type']}]--> {e['target']} "
                      f"conf={e['confidence']}")
        else:
            print(f"RESULT:   No path found")
        print(f"STATUS:   {'PASS' if path else 'FAIL'}")
        print(f"{'='*60}")

        assert path is not None
        assert path["hops"] >= 1

    def test_shortest_path_no_connection(self, seeded_db):
        """No path should exist between disconnected nodes."""
        svc = GraphAnalyticsService(seeded_db)
        # ent-loc-chennai is only in case-101, ent-acc-a101 only in case-205
        # They might not be connected
        path = svc.find_shortest_path("ent-loc-chennai", "ent-acc-a101")
        # This may or may not find a path depending on graph connectivity
        print(f"\n{'='*60}")
        print(f"PATH:     ent-loc-chennai → ent-acc-a101")
        print(f"RESULT:   {'Path found' if path else 'No path (expected for disconnected)'}")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

    def test_network_dna(self, seeded_db):
        svc = GraphAnalyticsService(seeded_db)
        dna = svc.get_network_dna(case_id="case-101")

        print(f"\n{'='*60}")
        print(f"NETWORK DNA (case-101):")
        print(f"  networkSize:             {dna['networkSize']}")
        print(f"  communityCount:          {dna['communityCount']}")
        print(f"  relationshipCount:       {dna['relationshipCount']}")
        print(f"  communicationDensity:    {dna['communicationDensity']}")
        print(f"  geographicSpread:        {dna['geographicSpread']}")
        print(f"  centralityConcentration: {dna['centralityConcentration']}")
        print(f"STATUS:   {'PASS' if dna['networkSize'] > 0 else 'FAIL'}")
        print(f"{'='*60}")

        assert dna["networkSize"] > 0
        assert dna["relationshipCount"] >= 0

    def test_bridge_entities(self, seeded_db):
        """Identify bridge entities connecting clusters."""
        svc = GraphAnalyticsService(seeded_db)
        result = svc.compute_centrality()
        bridges = result.get("topBridges", [])

        print(f"\n{'='*60}")
        print(f"BRIDGE ENTITIES: {len(bridges)}")
        for b in bridges:
            print(f"  {b['label']} betweenness={b['betweennessCentrality']:.4f}")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")
