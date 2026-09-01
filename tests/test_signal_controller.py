"""Independent tests for sequential signal pre-emption."""

from src.city_graph import build_city, node_id
from src.signal_controller import NORMAL, PREEMPT, corridor_signal_ids, preempt_plan


def test_only_next_signals_preempted():
    graph = build_city()
    path = [
        node_id(1, 1),
        node_id(2, 1),
        node_id(3, 1),
        node_id(4, 1),
        node_id(5, 1),
        node_id(6, 1),
    ]
    plan = preempt_plan(graph, path, ambulance_index=0, horizon=2)
    active = corridor_signal_ids(plan)
    assert len(active) == 2
    assert graph.nodes[node_id(2, 1)]["signal_id"] in active
    assert graph.nodes[node_id(3, 1)]["signal_id"] in active
    assert plan[graph.nodes[node_id(4, 1)]["signal_id"]] == NORMAL


def test_corridor_advances_with_ambulance():
    graph = build_city()
    path = [node_id(1, 1), node_id(2, 1), node_id(3, 1), node_id(4, 1)]
    first = preempt_plan(graph, path, ambulance_index=0, horizon=1)
    second = preempt_plan(graph, path, ambulance_index=1, horizon=1)
    assert first[graph.nodes[node_id(2, 1)]["signal_id"]] == PREEMPT
    assert second[graph.nodes[node_id(2, 1)]["signal_id"]] == NORMAL
    assert second[graph.nodes[node_id(3, 1)]["signal_id"]] == PREEMPT


def test_unrelated_signals_stay_normal():
    graph = build_city()
    path = [node_id(1, 1), node_id(1, 2)]
    plan = preempt_plan(graph, path, ambulance_index=0, horizon=2)
    far = graph.nodes[node_id(5, 5)]["signal_id"]
    assert plan[far] == NORMAL
