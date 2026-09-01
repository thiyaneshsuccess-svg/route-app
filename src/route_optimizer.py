"""Choose the route with lowest predicted emergency travel time."""

from __future__ import annotations

from typing import Mapping

import networkx as nx

from .traffic_simulator import CLOSED_TRAVEL_TIME_S


def _weight_graph(
    graph: nx.DiGraph,
    times: Mapping[tuple[str, str], float],
) -> nx.DiGraph:
    weighted = graph.copy()
    for u, v in list(weighted.edges()):
        t = times.get((u, v), CLOSED_TRAVEL_TIME_S)
        if t >= CLOSED_TRAVEL_TIME_S / 10:
            weighted.remove_edge(u, v)
        else:
            weighted[u][v]["emergency_s"] = float(t)
    return weighted


def shortest_path(
    graph: nx.DiGraph,
    origin: str,
    dest: str,
    times: Mapping[tuple[str, str], float],
) -> dict:
    weighted = _weight_graph(graph, times)
    path = nx.shortest_path(weighted, origin, dest, weight="emergency_s")
    edges = list(zip(path, path[1:]))
    total = sum(float(times[e]) for e in edges)
    return {"path": path, "edges": edges, "travel_time_s": total}


def optimize(
    graph: nx.DiGraph,
    origin: str,
    dest: str,
    predicted_times: Mapping[tuple[str, str], float],
) -> dict:
    """Min predicted emergency travel time (proposed system)."""
    return shortest_path(graph, origin, dest, predicted_times)


def baseline_route(
    graph: nx.DiGraph,
    origin: str,
    dest: str,
    current_times: Mapping[tuple[str, str], float],
) -> dict:
    """Route on current (or free-flow) times, not predicted congestion."""
    return shortest_path(graph, origin, dest, current_times)


def predicted_travel_times(
    graph: nx.DiGraph,
    predicted_congestion: Mapping[tuple[str, str], float],
    closed_edges: set[tuple[str, str]] | None = None,
) -> dict[tuple[str, str], float]:
    closed = closed_edges or set()
    times: dict[tuple[str, str], float] = {}
    for u, v, data in graph.edges(data=True):
        key = (u, v)
        if key in closed:
            times[key] = CLOSED_TRAVEL_TIME_S
            continue
        congestion = float(predicted_congestion.get(key, 0.0))
        free_flow = float(data["base_speed_kmh"])
        speed = max(3.0, free_flow * (1.0 - 0.85 * congestion))
        times[key] = float(data["length_m"]) / (speed / 3.6)
    return times
