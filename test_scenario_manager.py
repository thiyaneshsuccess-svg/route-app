"""Independent tests for scenario + closure state."""

from src.scenario_manager import ScenarioManager


def test_default_normal():
    mgr = ScenarioManager()
    assert mgr.name == "NORMAL"
    assert mgr.closed_edges == frozenset()


def test_set_rush_hour():
    mgr = ScenarioManager()
    mgr.set_scenario("RUSH_HOUR")
    mods = mgr.active_modifiers()
    assert mods["scenario"] == "RUSH_HOUR"
    assert mods["speed_multiplier"] < 1.0


def test_inject_road_closure():
    mgr = ScenarioManager()
    mgr.inject_road_closure("2_2", "2_3")
    assert mgr.name == "ROAD_CLOSURE"
    assert ("2_2", "2_3") in mgr.closed_edges
    mods = mgr.active_modifiers()
    assert ("2_2", "2_3") in mods["closed_edges"]


def test_leaving_closure_clears_edges():
    mgr = ScenarioManager()
    mgr.inject_road_closure("2_2", "2_3")
    mgr.set_scenario("NORMAL")
    assert mgr.closed_edges == frozenset()


def test_invalid_scenario_rejected():
    mgr = ScenarioManager()
    try:
        mgr.set_scenario("STORM")
        assert False, "expected ValueError"
    except ValueError:
        pass
