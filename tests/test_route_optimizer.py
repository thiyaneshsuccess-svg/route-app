"""Independent tests for predictive vs baseline routing."""

from src.city_graph import build_city, node_id
from src.route_optimizer import baseline_route, optimize, predicted_travel_times
from src.traffic_simulator import snapshot, travel_times


def test_optimize_finds_path():
    graph = build_city()
    snap = snapshot(graph, 12.0, scenario="NORMAL", seed=4)
    times = travel_times(snap)
    origin, dest = node_id(0, 0), node_id(7, 7)
    result = optimize(graph, origin, dest, times)
    assert result["path"][0] == origin
    assert result["path"][-1] == dest
    assert result["travel_time_s"] > 0
    assert len(result["edges"]) == len(result["path"]) - 1


def test_baseline_and_proposed_same_on_uniform_times():
    graph = build_city()
    snap = snapshot(graph, 3.0, scenario="NORMAL", seed=4)
    times = travel_times(snap)
    origin, dest = node_id(0, 0), node_id(5, 5)
    a = baseline_route(graph, origin, dest, times)
    b = optimize(graph, origin, dest, times)
    assert a["path"] == b["path"]


def test_closure_avoids_blocked_edge():
    graph = build_city()
    closed = (node_id(0, 0), node_id(0, 1))
    snap = snapshot(
        graph,
        12.0,
        scenario="ROAD_CLOSURE",
        closed_edges=[closed],
        seed=4,
    )
    times = travel_times(snap)
    result = optimize(graph, node_id(0, 0), node_id(0, 3), times)
    assert closed not in result["edges"]


def test_predicted_travel_times_slower_when_congested():
    graph = build_city()
    edge = (node_id(2, 2), node_id(2, 3))
    low = predicted_travel_times(graph, {edge: 0.1})
    high = predicted_travel_times(graph, {edge: 0.9})
    assert high[edge] > low[edge]
