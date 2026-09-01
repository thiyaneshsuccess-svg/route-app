"""Synthetic city road network. No traffic logic."""

from __future__ import annotations

import networkx as nx

GRID_SIZE = 8
BLOCK_LENGTH_M = 200.0
ARTERIAL_SPEED_KMH = 50.0
LOCAL_SPEED_KMH = 30.0
ARTERIAL_LANES = 3
LOCAL_LANES = 2
ARTERIAL_ROWS = (2, 5)
ARTERIAL_COLS = (2, 5)


def node_id(row: int, col: int) -> str:
    return f"{row}_{col}"


def parse_node(nid: str) -> tuple[int, int]:
    row_s, col_s = nid.split("_", 1)
    return int(row_s), int(col_s)


def is_arterial_node(row: int, col: int) -> bool:
    return row in ARTERIAL_ROWS or col in ARTERIAL_COLS


def is_internal_node(row: int, col: int, size: int = GRID_SIZE) -> bool:
    return 0 < row < size - 1 and 0 < col < size - 1


def signal_id_for(row: int, col: int, size: int = GRID_SIZE) -> str | None:
    if is_internal_node(row, col, size):
        return f"S{row}_{col}"
    return None


def edge_key(u: str, v: str) -> tuple[str, str]:
    return (u, v)


def signalized_nodes(graph: nx.DiGraph) -> set[str]:
    return {n for n, data in graph.nodes(data=True) if data.get("signal_id")}


def build_city(size: int = GRID_SIZE) -> nx.DiGraph:
    """Build a bidirectional grid city with arterial corridors and signals."""
    graph = nx.DiGraph()
    for row in range(size):
        for col in range(size):
            nid = node_id(row, col)
            graph.add_node(
                nid,
                row=row,
                col=col,
                x=float(col),
                y=float(size - 1 - row),
                signal_id=signal_id_for(row, col, size),
                is_arterial=is_arterial_node(row, col),
            )

    def add_directed(u: str, v: str) -> None:
        ur, uc = parse_node(u)
        vr, vc = parse_node(v)
        arterial = is_arterial_node(ur, uc) and is_arterial_node(vr, vc)
        dest_signal = graph.nodes[v].get("signal_id")
        graph.add_edge(
            u,
            v,
            length_m=BLOCK_LENGTH_M,
            lanes=ARTERIAL_LANES if arterial else LOCAL_LANES,
            base_speed_kmh=ARTERIAL_SPEED_KMH if arterial else LOCAL_SPEED_KMH,
            signal_id=dest_signal,
            is_arterial=arterial,
        )

    for row in range(size):
        for col in range(size):
            u = node_id(row, col)
            if col + 1 < size:
                v = node_id(row, col + 1)
                add_directed(u, v)
                add_directed(v, u)
            if row + 1 < size:
                v = node_id(row + 1, col)
                add_directed(u, v)
                add_directed(v, u)

    graph.graph["size"] = size
    graph.graph["block_length_m"] = BLOCK_LENGTH_M
    return graph
