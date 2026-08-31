"""
COMPONENT TEST: Temporal Analysis
===================================
Tests timeline event generation, date-range filtering, and temporal sequence analysis.
"""
import pytest
from app.services.analytics.graph_analytics import GraphAnalyticsService


class TestTemporalAnalysis:
    """Phase 13 — Temporal timeline evolution & timestamp verification."""

    def test_temporal_stats_aggregation(self, seeded_db):
        svc = GraphAnalyticsService(seeded_db)
        stats = svc.get_temporal_stats(case_id="case-101")

        events = stats.get("events", [])
        total = stats.get("totalEvents", 0)
        first_seen = stats.get("firstSeen")
        last_seen = stats.get("lastSeen")

        print(f"\n{'='*60}")
        print(f"TEMPORAL STATS (case-101):")
        print(f"  Total Events: {total}")
        print(f"  First Seen:   {first_seen}")
        print(f"  Last Seen:    {last_seen}")
        print(f"  Event List Length: {len(events)}")
        for e in events[:3]:
            print(f"    - {e['timestamp']}: {e['source']} --[{e['type']}]--> {e['target']}")
        print(f"STATUS:   {'PASS' if len(events) >= 1 else 'FAIL'}")
        print(f"{'='*60}")

        assert len(events) >= 1
        assert first_seen <= last_seen

    def test_date_filtered_network_graph(self, seeded_db):
        svc = GraphAnalyticsService(seeded_db)
        
        # Query with restrictive date window
        G_all, _ = svc.build_networkx_graph(case_id="case-101")
        G_filtered, _ = svc.build_networkx_graph(case_id="case-101", date_from="2026-01-01", date_to="2026-02-01")

        print(f"\n{'='*60}")
        print(f"TEMPORAL GRAPH FILTERING:")
        print(f"  Unfiltered Edges: {G_all.number_of_edges()}")
        print(f"  Filtered Edges (Jan 2026): {G_filtered.number_of_edges()}")
        print(f"STATUS:   {'PASS' if G_filtered.number_of_edges() <= G_all.number_of_edges() else 'FAIL'}")
        print(f"{'='*60}")

        assert G_filtered.number_of_edges() <= G_all.number_of_edges()
