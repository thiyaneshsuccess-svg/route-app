"""Baseline vs proposed KPIs. Pure functions, no I/O."""

from __future__ import annotations

from typing import Mapping, Sequence

CONGESTED_THRESHOLD = 0.55


def total_travel_time_s(route: Mapping) -> float:
    return float(route["travel_time_s"])


def number_of_stops(path: Sequence[str], signal_plan: Mapping[str, str], graph) -> int:
    """Stops = signalized nodes on the path that are not pre-empted."""
    stops = 0
    for nid in path[1:]:
        sid = graph.nodes[nid].get("signal_id")
        if sid and signal_plan.get(sid, "NORMAL") != "PREEMPT":
            stops += 1
    return stops


def time_in_congestion_s(
    edges: Sequence[tuple[str, str]],
    snap: Mapping[tuple[str, str], Mapping],
) -> float:
    total = 0.0
    for edge in edges:
        vals = snap[edge]
        if float(vals["congestion"]) >= CONGESTED_THRESHOLD:
            total += float(vals["travel_time_s"])
    return total


def corridor_coverage(
    path: Sequence[str],
    signal_plan: Mapping[str, str],
    graph,
) -> float:
    signal_nodes = [n for n in path[1:] if graph.nodes[n].get("signal_id")]
    if not signal_nodes:
        return 1.0
    preempted = sum(
        1
        for n in signal_nodes
        if signal_plan.get(graph.nodes[n]["signal_id"]) == "PREEMPT"
    )
    return preempted / len(signal_nodes)


def compare(baseline: Mapping, proposed: Mapping) -> dict[str, float]:
    """Dict of KPIs for Plotly. Each mapping needs travel_time_s, stops, congested_s, coverage."""
    b_t = float(baseline["travel_time_s"])
    p_t = float(proposed["travel_time_s"])
    saved = b_t - p_t
    return {
        "baseline_travel_time_s": b_t,
        "proposed_travel_time_s": p_t,
        "time_saved_s": saved,
        "improvement_pct": (saved / b_t * 100.0) if b_t else 0.0,
        "baseline_stops": float(baseline.get("stops", 0)),
        "proposed_stops": float(proposed.get("stops", 0)),
        "baseline_congested_s": float(baseline.get("congested_s", 0)),
        "proposed_congested_s": float(proposed.get("congested_s", 0)),
        "baseline_coverage": float(baseline.get("coverage", 0)),
        "proposed_coverage": float(proposed.get("coverage", 0)),
    }
