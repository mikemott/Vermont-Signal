"""
Community Detection for Entity Networks
Identifies thematic clusters using Louvain algorithm
"""

import logging
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict

try:
    import networkx as nx
    from networkx.algorithms import community as nx_community
except ImportError:
    nx = None
    nx_community = None
    logging.warning("NetworkX not installed. Install with: pip install networkx")

logger = logging.getLogger(__name__)


class CommunityDetector:
    """
    Detects communities (thematic clusters) in entity networks
    Uses Louvain method for modularity optimization
    """

    # Color palette for communities (20 distinct colors)
    COMMUNITY_COLORS = [
        '#e74c3c',  # Red
        '#3498db',  # Blue
        '#2ecc71',  # Green
        '#f39c12',  # Orange
        '#9b59b6',  # Purple
        '#1abc9c',  # Turquoise
        '#e67e22',  # Carrot
        '#34495e',  # Wet Asphalt
        '#16a085',  # Green Sea
        '#c0392b',  # Pomegranate
        '#27ae60',  # Nephritis
        '#2980b9',  # Belize Hole
        '#8e44ad',  # Wisteria
        '#d35400',  # Pumpkin
        '#c0392b',  # Alizarin
        '#7f8c8d',  # Asbestos
        '#2c3e50',  # Midnight Blue
        '#f1c40f',  # Sun Flower
        '#e74c3c',  # Alizarin (duplicate intentional for >18 communities)
        '#95a5a6',  # Concrete
    ]

    def __init__(self):
        """Initialize community detector"""
        if nx is None:
            raise ImportError("NetworkX is required. Install with: pip install networkx")

    def detect_communities(
        self,
        nodes: List[Dict],
        edges: List[Dict],
        resolution: float = 1.0,
        min_community_size: int = 2
    ) -> Dict[str, int]:
        """
        Detect communities using Louvain algorithm

        Args:
            nodes: List of node dicts with 'id', 'label', 'type', 'weight'
            edges: List of edge dicts with 'source', 'target', 'strength'
            resolution: Louvain resolution parameter (higher = more communities)
            min_community_size: Minimum nodes per community (smaller merged into -1)

        Returns:
            Dict mapping node_id -> community_id (0, 1, 2, ...)
        """
        if not nodes or not edges:
            # No edges = all nodes in community 0
            return {node['id']: 0 for node in nodes}

        # Build weighted graph
        G = nx.Graph()

        # Add nodes
        for node in nodes:
            G.add_node(node['id'], **node)

        # Add edges with weights (strength, npmi, or proximity)
        for edge in edges:
            weight = self._get_edge_weight(edge)
            G.add_edge(edge['source'], edge['target'], weight=weight)

        # Run Louvain community detection
        try:
            communities = nx_community.louvain_communities(
                G,
                weight='weight',
                resolution=resolution,
                seed=42  # Reproducible results
            )
        except Exception as e:
            logger.warning(f"Louvain failed, using connected components: {e}")
            # Fallback: use connected components
            communities = list(nx.connected_components(G))

        # Build node -> community_id mapping
        node_to_community = {}
        community_sizes = {}

        for comm_id, community_set in enumerate(communities):
            community_sizes[comm_id] = len(community_set)
            for node_id in community_set:
                node_to_community[node_id] = comm_id

        # Merge small communities into "other" (-1)
        if min_community_size > 1:
            node_to_community = self._merge_small_communities(
                node_to_community,
                community_sizes,
                min_community_size
            )

        logger.info(
            f"Detected {len(set(node_to_community.values()))} communities "
            f"(resolution={resolution}, min_size={min_community_size})"
        )

        return node_to_community

    def assign_community_colors(
        self,
        node_to_community: Dict[str, int]
    ) -> Dict[str, str]:
        """
        Assign colors to communities

        Args:
            node_to_community: Dict mapping node_id -> community_id

        Returns:
            Dict mapping node_id -> hex_color
        """
        # Get unique community IDs
        unique_communities = sorted(set(node_to_community.values()))

        # Build community -> color mapping
        community_colors = {}
        for idx, comm_id in enumerate(unique_communities):
            if comm_id == -1:
                # "Other" community gets gray
                community_colors[comm_id] = '#95a5a6'
            else:
                # Cycle through color palette
                community_colors[comm_id] = self.COMMUNITY_COLORS[idx % len(self.COMMUNITY_COLORS)]

        # Map nodes to colors
        node_colors = {}
        for node_id, comm_id in node_to_community.items():
            node_colors[node_id] = community_colors[comm_id]

        return node_colors

    def get_community_metadata(
        self,
        nodes: List[Dict],
        edges: List[Dict],
        node_to_community: Dict[str, int]
    ) -> List[Dict]:
        """
        Generate metadata about each community

        Args:
            nodes: List of node dicts
            edges: List of edge dicts
            node_to_community: Dict mapping node_id -> community_id

        Returns:
            List of community metadata dicts
        """
        # Group nodes by community
        communities = defaultdict(list)
        for node in nodes:
            node_id = node['id']
            comm_id = node_to_community.get(node_id, -1)
            communities[comm_id].append(node)

        # Calculate metadata for each community
        metadata = []
        for comm_id, comm_nodes in sorted(communities.items()):
            node_ids = {n['id'] for n in comm_nodes}

            # Count internal edges (within community)
            internal_edges = [
                e for e in edges
                if e['source'] in node_ids and e['target'] in node_ids
            ]

            # Count external edges (crossing communities)
            external_edges = [
                e for e in edges
                if (e['source'] in node_ids) != (e['target'] in node_ids)
            ]

            # Calculate cohesion (internal / total edges)
            total_edges = len(internal_edges) + len(external_edges)
            cohesion = len(internal_edges) / total_edges if total_edges > 0 else 0

            # Get most common entity types in community
            type_counts = defaultdict(int)
            for node in comm_nodes:
                type_counts[node.get('type', 'UNKNOWN')] += 1

            dominant_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else 'UNKNOWN'

            metadata.append({
                'community_id': comm_id,
                'size': len(comm_nodes),
                'internal_edges': len(internal_edges),
                'external_edges': len(external_edges),
                'cohesion': cohesion,
                'dominant_type': dominant_type,
                'node_ids': [n['id'] for n in comm_nodes],
                'top_entities': sorted(
                    comm_nodes,
                    key=lambda n: n.get('weight', 1),
                    reverse=True
                )[:5]  # Top 5 by weight
            })

        return metadata

    def create_super_nodes(
        self,
        nodes: List[Dict],
        edges: List[Dict],
        node_to_community: Dict[str, int],
        min_community_size: int = 5
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Collapse small communities into super-nodes for zoomed-out view

        Args:
            nodes: Original node list
            edges: Original edge list
            node_to_community: Node -> community mapping
            min_community_size: Communities smaller than this become super-nodes

        Returns:
            Tuple of (collapsed_nodes, collapsed_edges)
        """
        # Group nodes by community
        communities = defaultdict(list)
        for node in nodes:
            comm_id = node_to_community.get(node['id'], -1)
            communities[comm_id].append(node)

        # Separate large communities (keep as-is) vs small (collapse)
        super_nodes = []
        super_edges = []
        node_id_to_super_id = {}

        for comm_id, comm_nodes in communities.items():
            if len(comm_nodes) >= min_community_size:
                # Large community: keep all nodes
                for node in comm_nodes:
                    super_nodes.append(node)
                    node_id_to_super_id[node['id']] = node['id']
            else:
                # Small community: create super-node
                super_node_id = f"community_{comm_id}"
                total_weight = sum(n.get('weight', 1) for n in comm_nodes)

                super_nodes.append({
                    'id': super_node_id,
                    'label': f"Cluster {comm_id} ({len(comm_nodes)} entities)",
                    'type': 'COMMUNITY',
                    'weight': total_weight,
                    'is_super_node': True,
                    'member_count': len(comm_nodes),
                    'member_ids': [n['id'] for n in comm_nodes]
                })

                # Map all members to super-node
                for node in comm_nodes:
                    node_id_to_super_id[node['id']] = super_node_id

        # Rebuild edges with super-nodes
        edge_weights = defaultdict(float)  # (source, target) -> aggregated weight

        for edge in edges:
            src = node_id_to_super_id.get(edge['source'])
            tgt = node_id_to_super_id.get(edge['target'])

            if src and tgt and src != tgt:  # Skip self-loops
                edge_key = tuple(sorted([src, tgt]))  # Undirected
                weight = self._get_edge_weight(edge)
                edge_weights[edge_key] += weight

        # Convert aggregated edges back to list
        for (src, tgt), weight in edge_weights.items():
            super_edges.append({
                'source': src,
                'target': tgt,
                'strength': weight / 10,  # Normalize
                'label': 'clustered',
                'is_super_edge': True
            })

        logger.info(
            f"Created {len(super_nodes)} super-nodes from {len(nodes)} original nodes "
            f"({len(super_edges)} super-edges)"
        )

        return super_nodes, super_edges

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

    def _merge_small_communities(
        self,
        node_to_community: Dict[str, int],
        community_sizes: Dict[int, int],
        min_size: int
    ) -> Dict[str, int]:
        """
        Merge communities smaller than min_size into "other" (-1)

        Args:
            node_to_community: Original mapping
            community_sizes: Community -> size mapping
            min_size: Minimum community size

        Returns:
            Updated node_to_community with small communities merged
        """
        updated_mapping = {}

        for node_id, comm_id in node_to_community.items():
            if community_sizes[comm_id] < min_size:
                updated_mapping[node_id] = -1  # "Other"
            else:
                updated_mapping[node_id] = comm_id

        return updated_mapping
