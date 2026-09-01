"""Independent tests for the XGBoost ETA congestion model."""

from src.city_graph import build_city, node_id
from src.congestion_predictor import CongestionPredictor
from src.traffic_simulator import snapshot


def test_fit_and_predict_in_unit_interval():
    graph = build_city(4)
    pred = CongestionPredictor()
    mae = pred.fit(graph, seed=3)
    assert mae < 0.25
    snap = snapshot(graph, 8.0, scenario="NORMAL", seed=3)
    edge = (node_id(1, 1), node_id(1, 2))
    value = pred.predict_at_eta(
        graph,
        edge,
        eta_minutes=5.0,
        context={"hour": 8.0, "current_congestion": snap[edge]["congestion"]},
    )
    assert 0.0 <= value <= 1.0


def test_predict_graph_marks_closed_as_one():
    graph = build_city(4)
    pred = CongestionPredictor()
    pred.fit(graph, seed=1)
    closed = (node_id(0, 0), node_id(0, 1))
    snap = snapshot(
        graph,
        10.0,
        scenario="ROAD_CLOSURE",
        closed_edges=[closed],
        seed=1,
    )
    predicted = pred.predict_graph(graph, snap, eta_minutes=4.0, hour=10.0)
    assert predicted[closed] == 1.0
