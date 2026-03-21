"""Graph engine for OathFish MCP server.

Entity/relationship CRUD with temporal tracking and centrality computation.
5 MCP tools: graph_init, graph_add_node, graph_add_edge, graph_query, graph_compute_centrality.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from .models import (
    EdgeType,
    EntityType,
    GraphEdge,
    GraphNode,
    GraphOntology,
    GraphState,
)
from .persistence import atomic_write_json, read_json


class GraphEngine:
    """Entity/relationship storage with temporal tracking."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._state: GraphState | None = None

    def _state_path(self) -> Path:
        return self._data_dir / "graph" / "state.json"

    def _persist(self) -> None:
        assert self._state is not None
        atomic_write_json(self._state_path(), self._state)

    def _load(self) -> GraphState | None:
        data = read_json(self._state_path())
        if data is None:
            return None
        return GraphState.model_validate(data)

    def _ensure_loaded(self) -> GraphState:
        if self._state is None:
            self._state = self._load()
        if self._state is None:
            raise ValueError("No active graph. Call graph_init first.")
        return self._state

    def _resolve_node(self, name_or_id: str) -> GraphNode | None:
        """Resolve a node by ID or name."""
        state = self._ensure_loaded()
        if name_or_id in state.nodes:
            return state.nodes[name_or_id]
        for node in state.nodes.values():
            if node.name == name_or_id:
                return node
        return None

    def _edge_valid_at(self, edge: GraphEdge, as_of: str) -> bool:
        """Check if an edge is valid at a given time point.

        Supports both ISO timestamps and round labels (e.g., "round-3").
        """
        if edge.valid_at is not None and edge.valid_at > as_of:
            return False
        if edge.invalid_at is not None and edge.invalid_at <= as_of:
            return False
        return True

    async def graph_init(self, ontology: dict) -> dict:
        """Create graph with entity/relationship type definitions."""
        parsed_ontology = GraphOntology.model_validate(ontology)
        graph_id = f"graph-{uuid.uuid4().hex[:8]}"

        self._state = GraphState(
            graph_id=graph_id,
            ontology=parsed_ontology,
        )
        self._persist()

        return {
            "graph_id": graph_id,
            "entity_types_count": len(parsed_ontology.entity_types),
            "edge_types_count": len(parsed_ontology.edge_types),
        }

    async def graph_add_node(
        self,
        name: str,
        type: str,
        summary: str = "",
        attributes: dict | None = None,
    ) -> dict:
        """Add an entity node. Type must match ontology."""
        state = self._ensure_loaded()

        # Validate type against ontology
        valid_types = {et.name for et in state.ontology.entity_types}
        if type not in valid_types:
            raise ValueError(
                f"Entity type '{type}' not in ontology. Valid: {sorted(valid_types)}"
            )

        node_id = f"node-{uuid.uuid4().hex[:8]}"
        node = GraphNode(
            node_id=node_id,
            name=name,
            type=type,
            summary=summary,
            attributes=attributes or {},
        )
        state.nodes[node_id] = node
        self._persist()

        return {"node_id": node_id, "name": name, "type": type}

    async def graph_add_edge(
        self,
        from_node: str,
        to_node: str,
        type: str,
        facts: str = "",
        metadata: dict | None = None,
        valid_at: str | None = None,
        invalid_at: str | None = None,
    ) -> dict:
        """Add a relationship edge with optional temporal bounds."""
        state = self._ensure_loaded()

        # Validate edge type
        valid_types = {et.name for et in state.ontology.edge_types}
        if type not in valid_types:
            raise ValueError(
                f"Edge type '{type}' not in ontology. Valid: {sorted(valid_types)}"
            )

        # Resolve node references
        from_resolved = self._resolve_node(from_node)
        to_resolved = self._resolve_node(to_node)
        if from_resolved is None:
            raise ValueError(f"Node not found: {from_node}")
        if to_resolved is None:
            raise ValueError(f"Node not found: {to_node}")

        edge_id = f"edge-{uuid.uuid4().hex[:8]}"
        edge = GraphEdge(
            edge_id=edge_id,
            from_node=from_resolved.node_id,
            to_node=to_resolved.node_id,
            type=type,
            facts=facts,
            metadata=metadata or {},
            valid_at=valid_at,
            invalid_at=invalid_at,
        )
        state.edges[edge_id] = edge
        self._persist()

        return {
            "edge_id": edge_id,
            "from": from_resolved.node_id,
            "to": to_resolved.node_id,
            "type": type,
        }

    async def graph_query(
        self,
        name_or_id: str,
        depth: int = 1,
        as_of: str | None = None,
        max_results: int = 50,
    ) -> dict:
        """Return a node with edges and neighbors up to depth."""
        state = self._ensure_loaded()

        node = self._resolve_node(name_or_id)
        if node is None:
            return {"error": f"Node not found: {name_or_id}"}

        # BFS to collect edges and neighbors up to depth
        visited_nodes: set[str] = {node.node_id}
        result_edges: list[dict] = []
        frontier: set[str] = {node.node_id}

        for _ in range(depth):
            next_frontier: set[str] = set()
            for edge in state.edges.values():
                if len(result_edges) >= max_results:
                    break

                # Check temporal validity
                if as_of is not None and not self._edge_valid_at(edge, as_of):
                    continue

                if edge.from_node in frontier:
                    result_edges.append(edge.model_dump(mode="json"))
                    if edge.to_node not in visited_nodes:
                        next_frontier.add(edge.to_node)
                        visited_nodes.add(edge.to_node)
                elif edge.to_node in frontier:
                    result_edges.append(edge.model_dump(mode="json"))
                    if edge.from_node not in visited_nodes:
                        next_frontier.add(edge.from_node)
                        visited_nodes.add(edge.from_node)

            frontier = next_frontier
            if not frontier:
                break

        # Collect neighbor info
        neighbors = []
        for nid in visited_nodes:
            if nid != node.node_id and nid in state.nodes:
                neighbors.append(state.nodes[nid].model_dump(mode="json"))

        return {
            "node": node.model_dump(mode="json"),
            "edges": result_edges[:max_results],
            "neighbors": neighbors,
        }

    async def graph_compute_centrality(self) -> dict:
        """Rank all nodes by degree centrality."""
        state = self._ensure_loaded()

        degree: dict[str, int] = {nid: 0 for nid in state.nodes}
        for edge in state.edges.values():
            if edge.from_node in degree:
                degree[edge.from_node] += 1
            if edge.to_node in degree:
                degree[edge.to_node] += 1

        rankings = []
        for rank, (nid, deg) in enumerate(
            sorted(degree.items(), key=lambda x: x[1], reverse=True), 1
        ):
            node = state.nodes[nid]
            rankings.append({
                "node_id": nid,
                "name": node.name,
                "type": node.type,
                "degree": deg,
                "rank": rank,
            })

        return {"rankings": rankings}


def register_tools(app, data_dir: Path) -> None:
    """Register graph MCP tools on the server."""
    engine = GraphEngine(data_dir)

    @app.tool()
    async def graph_init(ontology: dict) -> dict:
        """Create a knowledge graph with entity/relationship type definitions.

        Args:
            ontology: {entity_types: [{name, description}], edge_types: [{name, description}]}
        """
        return await engine.graph_init(ontology)

    @app.tool()
    async def graph_add_node(
        name: str,
        type: str,
        summary: str = "",
        attributes: dict | None = None,
    ) -> dict:
        """Add an entity node to the knowledge graph. Type must match ontology.

        Args:
            name: Entity name
            type: Entity type (must be defined in ontology)
            summary: Brief description
            attributes: Optional key-value attributes
        """
        return await engine.graph_add_node(name, type, summary, attributes)

    @app.tool()
    async def graph_add_edge(
        from_node: str,
        to_node: str,
        type: str,
        facts: str = "",
        metadata: dict | None = None,
        valid_at: str | None = None,
        invalid_at: str | None = None,
    ) -> dict:
        """Add a relationship edge with optional temporal bounds.

        Args:
            from_node: Source node ID or name
            to_node: Target node ID or name
            type: Edge type (must be defined in ontology)
            facts: Description of the relationship
            metadata: Optional key-value metadata
            valid_at: When this fact became true (ISO timestamp or round label)
            invalid_at: When this fact became false (None = still valid)
        """
        return await engine.graph_add_edge(
            from_node, to_node, type, facts, metadata, valid_at, invalid_at
        )

    @app.tool()
    async def graph_query(
        name_or_id: str,
        depth: int = 1,
        as_of: str | None = None,
        max_results: int = 50,
    ) -> dict:
        """Query the knowledge graph for a node and its relationships.

        Args:
            name_or_id: Node ID or name to query
            depth: Traversal depth (default 1)
            as_of: Temporal filter -- only edges valid at this time (None = all edges)
            max_results: Maximum edges returned (default 50)
        """
        return await engine.graph_query(name_or_id, depth, as_of, max_results)

    @app.tool()
    async def graph_compute_centrality() -> dict:
        """Rank all nodes by degree centrality (number of connections)."""
        return await engine.graph_compute_centrality()
