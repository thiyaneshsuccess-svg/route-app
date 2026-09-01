"""Independent tests for the synthetic city graph."""

from src.city_graph import (
    GRID_SIZE,
    build_city,
    edge_key,
    node_id,
    signalized_nodes,
)


def test_build_city_grid_size():
    graph = build_city()
    assert graph.number_of_nodes() == GRID_SIZE * GRID_SIZE
    assert graph.number_of_edges() == 2 * (GRID_SIZE * (GRID_SIZE - 1) * 2)


def test_bidirectional_edges_and_attrs():
    graph = build_city()
    u, v = node_id(0, 0), node_id(0, 1)
    assert graph.has_edge(u, v)
    assert graph.has_edge(v, u)
    data = graph.edges[u, v]
    assert data["length_m"] > 0
    assert data["lanes"] >= 2
    assert data["base_speed_kmh"] > 0


def test_signalized_nodes_are_internal():
    graph = build_city()
    signals = signalized_nodes(graph)
    assert signals
    assert node_id(0, 0) not in signals
    assert node_id(3, 3) in signals
    assert graph.nodes[node_id(3, 3)]["signal_id"] == "S3_3"


def test_edge_key():
    assert edge_key("0_0", "0_1") == ("0_0", "0_1")
