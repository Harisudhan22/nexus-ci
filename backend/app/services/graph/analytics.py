import networkx as nx
from typing import Dict, List, Any

def run_network_analytics(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes degree centrality, betweenness centrality, connected components,
    and community cluster structures using NetworkX.
    """
    G = nx.Graph()
    for n in nodes:
        G.add_node(n["id"])
    for e in edges:
        G.add_edge(e["source"], e["target"])

    # Compute Centrality measures
    deg_centrality = nx.degree_centrality(G) if len(G) > 0 else {}
    between_centrality = nx.betweenness_centrality(G) if len(G) > 0 else {}
    
    # Community detection (label propagation or simple connected components)
    components = list(nx.connected_components(G))
    clusters = {}
    for cluster_idx, comp in enumerate(components):
        for node_id in comp:
            clusters[node_id] = f"cluster_{cluster_idx + 1}"

    # Calculate page rank
    try:
        pagerank = nx.pagerank(G, alpha=0.85) if len(G) > 0 else {}
    except Exception:
        pagerank = {n["id"]: 1.0 / max(1, len(G)) for n in nodes}

    # Find bridge entities
    # A node is a bridge if it connects nodes in different components when removed (articulation point)
    bridges = set()
    if len(G) > 0:
        try:
            bridges = set(nx.articulation_points(G))
        except Exception:
            pass

    # Compile result mapping
    results = {}
    for n in nodes:
        node_id = n["id"]
        results[node_id] = {
            "degree": G.degree(node_id) if node_id in G else 0,
            "centrality": round(deg_centrality.get(node_id, 0.0), 2),
            "betweenness": round(between_centrality.get(node_id, 0.0), 2),
            "pagerank": round(pagerank.get(node_id, 0.0), 3),
            "cluster": clusters.get(node_id, "cluster_1"),
            "isBridge": node_id in bridges
        }
        
    return results
