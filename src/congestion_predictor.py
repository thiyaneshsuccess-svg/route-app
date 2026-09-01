"""XGBoost congestion-at-ETA predictor. Train on synthetic simulator samples."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd
import xgboost as xgb
import networkx as nx

from .traffic_simulator import snapshot

FEATURE_COLUMNS = [
    "hour",
    "is_rush_pattern",
    "is_arterial",
    "lanes",
    "base_speed_kmh",
    "current_congestion",
    "horizon_min",
]


class CongestionPredictor:
    def __init__(self) -> None:
        self.model = xgb.XGBRegressor(
            n_estimators=40,
            max_depth=4,
            learning_rate=0.15,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="reg:squarederror",
            random_state=42,
            n_jobs=1,
        )
        self._fitted = False

    def generate_training_frame(
        self,
        graph: nx.DiGraph,
        n_hours: int = 24,
        horizons: tuple[int, ...] = (2, 5, 8, 12),
        seed: int = 7,
    ) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        edges = list(graph.edges(data=True))
        for hour in range(n_hours):
            current = snapshot(graph, float(hour), scenario="NORMAL", seed=seed)
            future_by_h: dict[int, dict] = {}
            for h in horizons:
                future_hour = (hour + h / 60.0) % 24.0
                future_by_h[h] = snapshot(graph, future_hour, scenario="NORMAL", seed=seed)
            for u, v, data in edges:
                key = (u, v)
                cur = current[key]["congestion"]
                for h in horizons:
                    rows.append(
                        {
                            "hour": hour,
                            "is_rush_pattern": int(hour in (7, 8, 9, 17, 18, 19)),
                            "is_arterial": int(bool(data.get("is_arterial"))),
                            "lanes": int(data["lanes"]),
                            "base_speed_kmh": float(data["base_speed_kmh"]),
                            "current_congestion": float(cur),
                            "horizon_min": float(h),
                            "target_congestion": float(future_by_h[h][key]["congestion"]),
                        }
                    )
        return pd.DataFrame(rows)

    def fit(self, graph: nx.DiGraph, seed: int = 7) -> float:
        frame = self.generate_training_frame(graph, seed=seed)
        x = frame[FEATURE_COLUMNS]
        y = frame["target_congestion"]
        self.model.fit(x, y)
        self._fitted = True
        pred = self.model.predict(x)
        return float(np.mean(np.abs(pred - y.to_numpy())))

    def predict_at_eta(
        self,
        graph: nx.DiGraph,
        edge: tuple[str, str],
        eta_minutes: float,
        context: Mapping[str, Any],
    ) -> float:
        if not self._fitted:
            raise RuntimeError("CongestionPredictor.fit() must be called first")
        u, v = edge
        data = graph.edges[u, v]
        hour = float(context["hour"]) % 24.0
        current = float(context["current_congestion"])
        row = pd.DataFrame(
            [
                {
                    "hour": hour,
                    "is_rush_pattern": int(hour in (7, 8, 9, 17, 18, 19) or context.get("scenario") == "RUSH_HOUR"),
                    "is_arterial": int(bool(data.get("is_arterial"))),
                    "lanes": int(data["lanes"]),
                    "base_speed_kmh": float(data["base_speed_kmh"]),
                    "current_congestion": current,
                    "horizon_min": float(eta_minutes),
                }
            ]
        )
        pred = float(self.model.predict(row[FEATURE_COLUMNS])[0])
        return float(np.clip(pred, 0.0, 1.0))

    def predict_graph(
        self,
        graph: nx.DiGraph,
        current_snap: Mapping[tuple[str, str], Mapping[str, Any]],
        eta_minutes: float,
        hour: float,
        scenario: str = "NORMAL",
    ) -> dict[tuple[str, str], float]:
        predicted: dict[tuple[str, str], float] = {}
        for edge, vals in current_snap.items():
            if vals.get("closed"):
                predicted[edge] = 1.0
                continue
            predicted[edge] = self.predict_at_eta(
                graph,
                edge,
                eta_minutes,
                {
                    "hour": hour,
                    "current_congestion": vals["congestion"],
                    "scenario": scenario,
                },
            )
        return predicted
