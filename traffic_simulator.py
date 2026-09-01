"""Deterministic synthetic traffic snapshots. Independent of routing."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

import numpy as np
import networkx as nx

SCENARIOS = ("NORMAL", "RUSH_HOUR", "ROAD_CLOSURE")
CLOSED_TRAVEL_TIME_S = 1e9


def _rush_factor(hour: float) -> float:
    morning = float(np.exp(-0.5 * ((hour - 8.0) / 1.4) ** 2))
    evening = float(np.exp(-0.5 * ((hour - 18.0) / 1.6) ** 2))
    return max(morning, evening)


def _default_closed_edge(graph: nx.DiGraph, seed: int) -> tuple[str, str]:
    arterials = [
        (u, v)
        for u, v, data in graph.edges(data=True)
        if data.get("is_arterial")
    ]
    if not arterials:
        arterials = list(graph.edges())
    idx = int(seed) % len(arterials)
    return arterials[idx]


def snapshot(
    graph: nx.DiGraph,
    time_of_day_hour: float,
    scenario: str = "NORMAL",
    closed_edges: Iterable[tuple[str, str]] | None = None,
    seed: int = 42,
) -> dict[tuple[str, str], dict[str, Any]]:
    """Return per-edge congestion in [0, 1] and travel_time_s.

    Deterministic for a given graph, hour, scenario, closed_edges, and seed.
    """
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario {scenario!r}; expected one of {SCENARIOS}")

    closed = set(closed_edges or ())
    if scenario == "ROAD_CLOSURE" and not closed:
        closed.add(_default_closed_edge(graph, seed))

    hour = float(time_of_day_hour) % 24.0
    rush = _rush_factor(hour)
    if scenario == "RUSH_HOUR":
        base = min(1.0, 0.35 + 0.55 * rush)
    else:
        base = 0.12 + 0.35 * rush

    rng = np.random.default_rng(int(seed) + int(round(hour * 4)))
    result: dict[tuple[str, str], dict[str, Any]] = {}

    for u, v, data in graph.edges(data=True):
        key = (u, v)
        if key in closed:
            result[key] = {
                "congestion": 1.0,
                "travel_time_s": CLOSED_TRAVEL_TIME_S,
                "speed_kmh": 0.0,
                "closed": True,
            }
            continue

        arterial_boost = 0.12 if data.get("is_arterial") and scenario == "RUSH_HOUR" else 0.0
        noise = float(rng.uniform(-0.04, 0.04))
        congestion = float(np.clip(base + arterial_boost + noise, 0.0, 1.0))
        free_flow = float(data["base_speed_kmh"])
        speed = max(3.0, free_flow * (1.0 - 0.85 * congestion))
        length_m = float(data["length_m"])
        travel_time_s = length_m / (speed / 3.6)
        result[key] = {
            "congestion": congestion,
            "travel_time_s": float(travel_time_s),
            "speed_kmh": float(speed),
            "closed": False,
        }
    return result


def travel_times(
    snap: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[tuple[str, str], float]:
    return {edge: float(vals["travel_time_s"]) for edge, vals in snap.items()}
