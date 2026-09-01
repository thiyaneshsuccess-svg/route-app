"""Scenario and incident state. Independent of routing."""

from __future__ import annotations

SCENARIOS = ("NORMAL", "RUSH_HOUR", "ROAD_CLOSURE")
ScenarioName = str


class ScenarioManager:
    """Mutable scenario + road-closure list for the simulator."""

    def __init__(self, name: ScenarioName = "NORMAL") -> None:
        self._name = "NORMAL"
        self._closed: set[tuple[str, str]] = set()
        self.set_scenario(name)

    def set_scenario(self, name: ScenarioName) -> None:
        if name not in SCENARIOS:
            raise ValueError(f"Unknown scenario {name!r}; expected one of {SCENARIOS}")
        self._name = name
        if name != "ROAD_CLOSURE":
            self._closed.clear()

    def inject_road_closure(self, u: str, v: str) -> None:
        self._name = "ROAD_CLOSURE"
        self._closed.add((u, v))

    def clear_closures(self) -> None:
        self._closed.clear()
        if self._name == "ROAD_CLOSURE":
            self._name = "NORMAL"

    def active_modifiers(self) -> dict:
        return {
            "scenario": self._name,
            "closed_edges": frozenset(self._closed),
            "speed_multiplier": 0.55 if self._name == "RUSH_HOUR" else 1.0,
        }

    @property
    def name(self) -> ScenarioName:
        return self._name

    @property
    def closed_edges(self) -> frozenset[tuple[str, str]]:
        return frozenset(self._closed)


def set_scenario(manager: ScenarioManager, name: ScenarioName) -> None:
    manager.set_scenario(name)


def inject_road_closure(manager: ScenarioManager, u: str, v: str) -> None:
    manager.inject_road_closure(u, v)


def active_modifiers(manager: ScenarioManager) -> dict:
    return manager.active_modifiers()
