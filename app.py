import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import plotly.graph_objects as go
import streamlit as st

from src.city_graph import build_city, node_id
from src.congestion_predictor import CongestionPredictor
from src.metrics import (
    compare,
    corridor_coverage,
    number_of_stops,
    time_in_congestion_s,
)
from src.route_optimizer import baseline_route, optimize, predicted_travel_times
from src.scenario_manager import ScenarioManager
from src.signal_controller import PREEMPT, preempt_plan
from src.traffic_simulator import snapshot, travel_times

st.set_page_config(page_title="Ambulance Green Corridor", layout="wide")


@st.cache_resource
def load_city():
    return build_city()


@st.cache_resource
def load_predictor(_graph):
    pred = CongestionPredictor()
    pred.fit(_graph, seed=7)
    return pred


def _edge_xy(graph, u, v):
    return [graph.nodes[u]["x"], graph.nodes[v]["x"]], [
        graph.nodes[u]["y"],
        graph.nodes[v]["y"],
    ]


def congestion_color(value: float, closed: bool) -> str:
    if closed:
        return "#111111"
    if value < 0.35:
        return "#2ecc71"
    if value < 0.65:
        return "#f1c40f"
    return "#e74c3c"


def make_map(graph, snap, route_edges, preempt_nodes, ambulance_node, dest_node):
    fig = go.Figure()
    for u, v, _ in graph.edges(data=True):
        xs, ys = _edge_xy(graph, u, v)
        vals = snap[(u, v)]
        width = 6 if (u, v) in route_edges else 2
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line=dict(color=congestion_color(vals["congestion"], vals["closed"]), width=width),
                hoverinfo="text",
                text=f"{u}→{v} congestion={vals['congestion']:.2f}",
                showlegend=False,
            )
        )
    nx_ = [graph.nodes[n]["x"] for n in graph.nodes]
    ny_ = [graph.nodes[n]["y"] for n in graph.nodes]
    fig.add_trace(
        go.Scatter(
            x=nx_,
            y=ny_,
            mode="markers",
            marker=dict(size=8, color="#7f8c8d"),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    if preempt_nodes:
        fig.add_trace(
            go.Scatter(
                x=[graph.nodes[n]["x"] for n in preempt_nodes],
                y=[graph.nodes[n]["y"] for n in preempt_nodes],
                mode="markers",
                marker=dict(size=16, color="#27ae60", symbol="diamond"),
                name="Pre-empted signal",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=[graph.nodes[ambulance_node]["x"]],
            y=[graph.nodes[ambulance_node]["y"]],
            mode="markers+text",
            marker=dict(size=18, color="#8e44ad"),
            text=["Ambulance"],
            textposition="top center",
            name="Ambulance",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[graph.nodes[dest_node]["x"]],
            y=[graph.nodes[dest_node]["y"]],
            mode="markers+text",
            marker=dict(size=18, color="#c0392b", symbol="x"),
            text=["Hospital"],
            textposition="top center",
            name="Hospital",
        )
    )
    fig.update_layout(
        height=640,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor="x"),
        title="City traffic (green=free, yellow=busy, red=congested, black=closed)",
        legend=dict(orientation="h"),
    )
    return fig


def kpis_for(route, snap, plan, graph):
    return {
        "travel_time_s": route["travel_time_s"],
        "stops": number_of_stops(route["path"], plan, graph),
        "congested_s": time_in_congestion_s(route["edges"], snap),
        "coverage": corridor_coverage(route["path"], plan, graph),
    }


def main():
    graph = load_city()
    predictor = load_predictor(graph)
    origin = node_id(0, 1)
    dest = node_id(7, 6)

    if "scenario" not in st.session_state:
        st.session_state.scenario = ScenarioManager("NORMAL")
        st.session_state.dispatched = False
        st.session_state.ambulance_index = 0
        st.session_state.hour = 8.0
        st.session_state.closure_injected = False

    mgr: ScenarioManager = st.session_state.scenario

    st.title("AI/ML Intelligent Ambulance Green Corridor")
    st.caption("Software-only simulation: predict congestion at ETA, pick the fastest emergency route, pre-empt signals in sequence.")

    left, right = st.columns([2, 1])
    with right:
        st.subheader("Demo controls")
        st.session_state.hour = st.slider("Time of day (hour)", 0.0, 23.5, float(st.session_state.hour), 0.5)
        scenario_choice = st.selectbox(
            "Scenario",
            ["NORMAL", "RUSH_HOUR", "ROAD_CLOSURE"],
            index=["NORMAL", "RUSH_HOUR", "ROAD_CLOSURE"].index(mgr.name),
        )
        if scenario_choice != mgr.name and scenario_choice != "ROAD_CLOSURE":
            mgr.set_scenario(scenario_choice)
            st.session_state.closure_injected = False

        if st.button("1. Dispatch ambulance", type="primary"):
            st.session_state.dispatched = True
            st.session_state.ambulance_index = 0

        if st.button("6. Inject road closure"):
            closed = (node_id(3, 3), node_id(3, 4))
            mgr.inject_road_closure(*closed)
            st.session_state.closure_injected = True

        if st.button("Advance ambulance (update corridor)"):
            st.session_state.ambulance_index += 1

        if st.button("Reset demo"):
            st.session_state.scenario = ScenarioManager("NORMAL")
            st.session_state.dispatched = False
            st.session_state.ambulance_index = 0
            st.session_state.closure_injected = False
            st.rerun()

    closed = list(mgr.closed_edges)
    current = snapshot(
        graph,
        st.session_state.hour,
        scenario=mgr.name,
        closed_edges=closed,
        seed=42,
    )
    current_times = travel_times(current)
    eta_minutes = 8.0
    predicted_cong = predictor.predict_graph(
        graph, current, eta_minutes, st.session_state.hour, scenario=mgr.name
    )
    predicted_times = predicted_travel_times(graph, predicted_cong, set(closed))

    try:
        proposed = optimize(graph, origin, dest, predicted_times)
        baseline = baseline_route(graph, origin, dest, current_times)
    except Exception as exc:
        st.error(f"No route available (closure blocking network): {exc}")
        return

    idx = min(st.session_state.ambulance_index, len(proposed["path"]) - 1)
    ambulance_node = proposed["path"][idx] if st.session_state.dispatched else origin
    plan = (
        preempt_plan(graph, proposed["path"], ambulance_index=idx, horizon=2)
        if st.session_state.dispatched
        else {graph.nodes[n]["signal_id"]: "NORMAL" for n in graph.nodes if graph.nodes[n].get("signal_id")}
    )
    idle_plan = {
        graph.nodes[n]["signal_id"]: "NORMAL"
        for n in graph.nodes
        if graph.nodes[n].get("signal_id")
    }
    preempt_nodes = [
        n
        for n in proposed["path"]
        if graph.nodes[n].get("signal_id") and plan.get(graph.nodes[n]["signal_id"]) == PREEMPT
    ]
    route_edges = set(proposed["edges"]) if st.session_state.dispatched else set()

    with left:
        st.plotly_chart(
            make_map(
                graph,
                current,
                route_edges,
                preempt_nodes,
                ambulance_node,
                dest,
            ),
            use_container_width=True,
        )

    m1, m2, m3, m4 = st.columns(4)
    avg_now = sum(v["congestion"] for v in current.values()) / len(current)
    avg_pred = sum(predicted_cong.values()) / len(predicted_cong)
    m1.metric("Current avg congestion", f"{avg_now:.2f}")
    m2.metric(f"Predicted avg @ +{int(eta_minutes)} min", f"{avg_pred:.2f}")
    m3.metric("Proposed travel time", f"{proposed['travel_time_s']:.0f} s")
    m4.metric("Baseline travel time", f"{baseline['travel_time_s']:.0f} s")

    if st.session_state.closure_injected:
        st.warning(
            "Incident detected: road closure on 3_3 → 3_4. Ambulance rerouted; green corridor updated."
        )

    if st.session_state.dispatched:
        base_k = kpis_for(baseline, current, idle_plan, graph)
        prop_k = kpis_for(proposed, current, plan, graph)
        cmp = compare(base_k, prop_k)
        st.subheader("Baseline vs proposed")
        st.bar_chart(
            {
                "travel_time_s": [cmp["baseline_travel_time_s"], cmp["proposed_travel_time_s"]],
                "stops": [cmp["baseline_stops"], cmp["proposed_stops"]],
            }
        )
        st.json(cmp)
        st.write("Proposed path:", " → ".join(proposed["path"]))
        st.write("Active pre-empted signals:", ", ".join(sorted(preempt_nodes)) or "(none)")


if __name__ == "__main__":
    main()
