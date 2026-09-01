"""Sequential traffic-signal pre-emption along the ambulance route."""

from __future__ import annotations

from typing import Sequence

PREEMPT = "PREEMPT"
NORMAL = "NORMAL"
CORRIDOR_AHEAD = 2


def upcoming_signals(
    graph,
    path: Sequence[str],
    ambulance_index: int,
) -> list[str]:
    """Signal ids on remaining nodes after the ambulance's current node."""
    signals: list[str] = []
    for nid in path[ambulance_index + 1 :]:
        sid = graph.nodes[nid].get("signal_id")
        if sid:
            signals.append(sid)
    return signals


def preempt_plan(
    graph,
    path: Sequence[str],
    ambulance_index: int = 0,
    horizon: int = CORRIDOR_AHEAD,
) -> dict[str, str]:
    """Only the next `horizon` upcoming signals are PREEMPT; others NORMAL."""
    all_ids = {
        data["signal_id"]
        for _, data in graph.nodes(data=True)
        if data.get("signal_id")
    }
    upcoming = upcoming_signals(graph, path, ambulance_index)
    active = set(upcoming[: max(0, horizon)])
    return {sid: (PREEMPT if sid in active else NORMAL) for sid in all_ids}


def corridor_signal_ids(plan: dict[str, str]) -> list[str]:
    return [sid for sid, state in plan.items() if state == PREEMPT]
