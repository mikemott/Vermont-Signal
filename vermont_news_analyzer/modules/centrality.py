"""
Centrality Metrics for Entity Networks
Computes PageRank, betweenness, and other network importance measures
"""

import logging
from typing import Dict, List, Tuple, Optional

try:
    import networkx as nx
except ImportError:
    nx = None
    logging.warning("NetworkX not installed. Install with: pip install networkx")

logger = logging.getLogger(__name__)


class CentralityCalculator:
    """
    Computes centrality metrics for entity networks
    Supports PageRank, betweenness, degree, and eigenvector centrality
    """

    def __init__(self):
        """Initialize centrality calculator"""
        if nx is None:
            raise ImportError("NetworkX is required. Install with: pip install networkx")

    def calculate_pagerank(
        self,
        nodes: List[Dict],
        edges: List[Dict],
        alpha: float = 0.85,
        max_iter: int = 100
    ) -> Dict[str, float]:
        """
        Calculate PageRank centrality for all nodes

        PageRank identifies "hub" entities that:
        - Have many connections
        - Connect to other important entities
        - Bridge different parts of the network

        Args:
            nodes: List of node dicts with 'id', 'label', 'type'
            edges: List of edge dicts with 'source', 'target', 'strength'
            alpha: Damping parameter (0.85 = standard)
            max_iter: Maximum iterations for convergence

        Returns:
            Dict mapping node_id -> pagerank_score (0.0-1.0)
        """
        if not nodes or not edges:
            # No edges = all nodes equal PageRank
            return {node['id']: 1.0 / len(nodes) for node in nodes}

        # Build weighted graph
        G = nx.Graph()

        # Add nodes
        for node in nodes:
            G.add_node(node['id'])

        # Add edges with weights (strength, npmi, or proximity)
        for edge in edges:
            weight = self._get_edge_weight(edge)
            G.add_edge(edge['source'], edge['target'], weight=weight)

        # Calculate PageRank with weight-aware random walk
        try:
            pagerank = nx.pagerank(
                G,
                alpha=alpha,
                max_iter=max_iter,
                weight='weight'
            )
            logger.info(f"Computed PageRank for {len(pagerank)} nodes")
            return pagerank

        except Exception as e:
            logger.error(f"PageRank calculation failed: {e}")
            # Fallback: uniform distribution
            return {node['id']: 1.0 / len(nodes) for node in nodes}

    def calculate_betweenness(
        self,
        nodes: List[Dict],
        edges: List[Dict],
        normalized: bool = True
    ) -> Dict[str, float]:
        """
        Calculate betweenness centrality for all nodes

        Betweenness identifies "bridge" entities that:
        - Connect different communities
        - Lie on shortest paths between many node pairs
        - Control information flow

        Args:
            nodes: List of node dicts
            edges: List of edge dicts
            normalized: Whether to normalize scores to [0, 1]

        Returns:
            Dict mapping node_id -> betweenness_score
        """
        if not nodes or not edges:
            return {node['id']: 0.0 for node in nodes}

        # Build weighted graph
        G = nx.Graph()
        for node in nodes:
            G.add_node(node['id'])
        for edge in edges:
            weight = self._get_edge_weight(edge)
            # Invert weight for shortest path (higher weight = shorter distance)
            G.add_edge(edge['source'], edge['target'], weight=1.0 / (weight + 0.01))

        try:
            betweenness = nx.betweenness_centrality(
                G,
                normalized=normalized,
                weight='weight'
            )
            logger.info(f"Computed betweenness for {len(betweenness)} nodes")
            return betweenness

        except Exception as e:
            logger.error(f"Betweenness calculation failed: {e}")
            return {node['id']: 0.0 for node in nodes}

    def calculate_degree_centrality(
        self,
        nodes: List[Dict],
        edges: List[Dict],
        weighted: bool = True
    ) -> Dict[str, float]:
        """
        Calculate degree centrality for all nodes

        Degree centrality measures:
        - Number of connections (unweighted)
        - Sum of connection strengths (weighted)

        Args:
            nodes: List of node dicts
            edges: List of edge dicts
            weighted: Whether to use weighted degree

        Returns:
            Dict mapping node_id -> degree_centrality
        """
        # Initialize degree counts
        degree = {node['id']: 0.0 for node in nodes}

        # Count connections
        for edge in edges:
            src, tgt = edge['source'], edge['target']
            weight = self._get_edge_weight(edge) if weighted else 1.0

            if src in degree:
                degree[src] += weight
            if tgt in degree:
                degree[tgt] += weight

        # Normalize to [0, 1] range
        max_degree = max(degree.values()) if degree.values() else 1.0
        if max_degree > 0:
            degree = {node_id: score / max_degree for node_id, score in degree.items()}

        logger.info(f"Computed degree centrality for {len(degree)} nodes")
        return degree

    def calculate_eigenvector_centrality(
        self,
        nodes: List[Dict],
        edges: List[Dict],
        max_iter: int = 100
    ) -> Dict[str, float]:
        """
        Calculate eigenvector centrality for all nodes

        Eigenvector centrality measures:
        - Connections to other well-connected nodes
        - Quality of neighbors (not just quantity)

        Args:
            nodes: List of node dicts
            edges: List of edge dicts
            max_iter: Maximum iterations

        Returns:
            Dict mapping node_id -> eigenvector_centrality
        """
        if not nodes or not edges:
            return {node['id']: 0.0 for node in nodes}

        # Build weighted graph
        G = nx.Graph()
        for node in nodes:
            G.add_node(node['id'])
        for edge in edges:
            weight = self._get_edge_weight(edge)
            G.add_edge(edge['source'], edge['target'], weight=weight)

        try:
            eigenvector = nx.eigenvector_centrality(
                G,
                max_iter=max_iter,
                weight='weight'
            )
            logger.info(f"Computed eigenvector centrality for {len(eigenvector)} nodes")
            return eigenvector

        except Exception as e:
            logger.warning(f"Eigenvector centrality failed, falling back to degree: {e}")
            # Fallback: use degree centrality
            return self.calculate_degree_centrality(nodes, edges, weighted=True)

    def calculate_all_metrics(
        self,
        nodes: List[Dict],
        edges: List[Dict]
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate all centrality metrics at once

        Args:
            nodes: List of node dicts
            edges: List of edge dicts

        Returns:
            Dict mapping node_id -> {'pagerank': X, 'betweenness': Y, ...}
        """
        logger.info(f"Computing all centrality metrics for {len(nodes)} nodes...")

        pagerank = self.calculate_pagerank(nodes, edges)
        betweenness = self.calculate_betweenness(nodes, edges)
        degree = self.calculate_degree_centrality(nodes, edges)
        eigenvector = self.calculate_eigenvector_centrality(nodes, edges)

        # Combine into single dict
        all_metrics = {}
        for node in nodes:
            node_id = node['id']
            all_metrics[node_id] = {
                'pagerank': pagerank.get(node_id, 0.0),
                'betweenness': betweenness.get(node_id, 0.0),
                'degree': degree.get(node_id, 0.0),
                'eigenvector': eigenvector.get(node_id, 0.0)
            }

        return all_metrics

    def rank_nodes(
        self,
        nodes: List[Dict],
        centrality_scores: Dict[str, float],
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Rank nodes by centrality score

        Args:
            nodes: List of node dicts
            centrality_scores: Dict of node_id -> score
            top_k: Number of top nodes to return

        Returns:
            List of (node_id, score) tuples, sorted descending
        """
        ranked = sorted(
            centrality_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return ranked[:top_k]

    def normalize_scores(
        self,
        scores: Dict[str, float],
        min_val: float = 0.0,
        max_val: float = 1.0
    ) -> Dict[str, float]:
        """
        Normalize scores to [min_val, max_val] range

        Args:
            scores: Dict of node_id -> score
            min_val: Minimum output value
            max_val: Maximum output value

        Returns:
            Normalized scores dict
        """
        if not scores:
            return {}

        current_min = min(scores.values())
        current_max = max(scores.values())
        range_size = current_max - current_min

        if range_size == 0:
            # All scores equal
            return {node_id: (min_val + max_val) / 2 for node_id in scores}

        normalized = {}
        for node_id, score in scores.items():
            # Map [current_min, current_max] -> [min_val, max_val]
            normalized_score = min_val + ((score - current_min) / range_size) * (max_val - min_val)
            normalized[node_id] = normalized_score

        return normalized

    def _get_edge_weight(self, edge: Dict) -> float:
        """
        Extract numeric weight from edge dict

        Args:
            edge: Edge dict with strength/npmi/proximity_weight

        Returns:
            Numeric weight (default 1.0)
        """
        if 'strength' in edge and edge['strength']:
            return float(edge['strength'])
        elif 'npmi' in edge and edge['npmi']:
            return max(0, float(edge['npmi']))  # NPMI can be negative
        elif 'proximity_weight' in edge and edge['proximity_weight']:
            return float(edge['proximity_weight']) / 10  # Normalize
        else:
            return 1.0
