"""Independent tests for baseline vs proposed KPIs."""

from src.city_graph import build_city, node_id
from src.metrics import compare, corridor_coverage, number_of_stops, time_in_congestion_s
from src.signal_controller import preempt_plan
from src.traffic_simulator import snapshot


def test_compare_reports_improvement():
    out = compare(
        {"travel_time_s": 100.0, "stops": 4, "congested_s": 40.0, "coverage": 0.0},
        {"travel_time_s": 80.0, "stops": 1, "congested_s": 20.0, "coverage": 0.5},
    )
    assert out["time_saved_s"] == 20.0
    assert out["improvement_pct"] == 20.0
    assert out["proposed_stops"] == 1


def test_stops_and_coverage():
    graph = build_city()
    path = [node_id(1, 1), node_id(2, 1), node_id(3, 1), node_id(4, 1)]
    plan = preempt_plan(graph, path, ambulance_index=0, horizon=2)
    stops = number_of_stops(path, plan, graph)
    coverage = corridor_coverage(path, plan, graph)
    assert stops == 1
    assert 0.0 < coverage < 1.0


def test_time_in_congestion():
    graph = build_city()
    edge = (node_id(0, 0), node_id(0, 1))
    snap = snapshot(graph, 8.0, scenario="RUSH_HOUR", seed=5)
    snap = dict(snap)
    snap[edge] = {**snap[edge], "congestion": 0.9, "travel_time_s": 40.0}
    assert time_in_congestion_s([edge], snap) == 40.0
