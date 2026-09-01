"""Independent tests for deterministic traffic snapshots."""

import math

from src.city_graph import build_city, node_id
from src.traffic_simulator import CLOSED_TRAVEL_TIME_S, snapshot, travel_times


def test_snapshot_covers_all_edges():
    graph = build_city()
    snap = snapshot(graph, 10.0, scenario="NORMAL", seed=1)
    assert set(snap) == set(graph.edges())


def test_congestion_bounds_and_travel_time():
    graph = build_city()
    snap = snapshot(graph, 10.0, scenario="NORMAL", seed=1)
    for vals in snap.values():
        assert 0.0 <= vals["congestion"] <= 1.0
        assert vals["travel_time_s"] > 0
        assert vals["closed"] is False


def test_deterministic_given_seed():
    graph = build_city()
    a = snapshot(graph, 8.0, scenario="RUSH_HOUR", seed=99)
    b = snapshot(graph, 8.0, scenario="RUSH_HOUR", seed=99)
    assert travel_times(a) == travel_times(b)


def test_rush_hour_more_congested_than_normal_midday():
    graph = build_city()
    normal = snapshot(graph, 8.0, scenario="NORMAL", seed=2)
    rush = snapshot(graph, 8.0, scenario="RUSH_HOUR", seed=2)
    avg = lambda s: sum(v["congestion"] for v in s.values()) / len(s)
    assert avg(rush) > avg(normal)


def test_road_closure_marks_edge():
    graph = build_city()
    closed = (node_id(2, 2), node_id(2, 3))
    snap = snapshot(
        graph,
        12.0,
        scenario="ROAD_CLOSURE",
        closed_edges=[closed],
        seed=3,
    )
    assert snap[closed]["closed"] is True
    assert snap[closed]["travel_time_s"] == CLOSED_TRAVEL_TIME_S
    assert math.isinf(snap[closed]["speed_kmh"]) or snap[closed]["speed_kmh"] == 0.0
