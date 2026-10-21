from types import SimpleNamespace

import pandas as pd
import pytest

from oemof.eesyplan import CarrierBus
from oemof.eesyplan import Demand
from oemof.eesyplan.postprocessing.KPIs import LCOE
from oemof.eesyplan.postprocessing.KPIs import _solver_value
from oemof.eesyplan.postprocessing.KPIs import get_objective
from oemof.eesyplan.postprocessing.KPIs import normalize_imported_results
from oemof.eesyplan.postprocessing.print_results import print_results


class DummyResults:
    def __init__(self, data=None, solver=None):
        self._data = data or {}
        self.solver = solver

    def keys(self):
        return set(self._data.keys())

    def __contains__(self, key):
        return key in self._data

    def __getitem__(self, key):
        return self._data[key]


class DummyNode:
    def __init__(self, label, node_type=None):
        self.label = label
        self.parent = None
        self._type = node_type

    def __class_getitem__(cls, item):
        return cls


class DummyES:
    def __init__(self, nodes):
        self.nodes = nodes


def test_solver_value_from_series():
    results = DummyResults(
        solver=pd.Series(
            {
                "objective": 123.45,
                "solver": "cbc",
                "termination_condition": "optimal",
            }
        )
    )
    assert _solver_value(results, "objective") == 123.45
    assert _solver_value(results, "solver") == "cbc"
    assert _solver_value(results, "termination_condition") == "optimal"
    assert _solver_value(results, "missing") is None


def test_solver_value_from_dict_like():
    results = DummyResults(solver={"objective": 10, "solver": "glpk"})
    assert _solver_value(results, "objective") == 10
    assert _solver_value(results, "solver") == "glpk"


def test_solver_value_from_object():
    results = DummyResults(
        solver=SimpleNamespace(objective=5.5, solver="highs")
    )
    assert _solver_value(results, "objective") == 5.5
    assert _solver_value(results, "solver") == "highs"


def test_solver_value_no_solver():
    results = DummyResults()
    assert _solver_value(results, "objective") is None


def test_get_objective_from_solver_series_string():
    results = DummyResults(
        solver=pd.Series({"objective": "62137253.933979616"})
    )
    assert get_objective(results) == 62137253.933979616


def test_get_objective_from_solver_series_float():
    results = DummyResults(solver=pd.Series({"objective": 1234.56}))
    assert get_objective(results) == 1234.56


def test_get_objective_from_solver_dict():
    results = DummyResults(solver={"objective": "100.0"})
    assert get_objective(results) == 100.0


def test_get_objective_from_solver_namespace():
    results = DummyResults(solver=SimpleNamespace(objective=42))
    assert get_objective(results) == 42.0


def test_get_objective_legacy_key():
    results = DummyResults(data={"objective": 20000.0})
    assert get_objective(results) == 20000.0


def test_get_objective_legacy_key_string():
    results = DummyResults(data={"objective": "555.5"})
    assert get_objective(results) == 555.5


def test_get_objective_raises_when_missing():
    results = DummyResults()
    with pytest.raises(ValueError, match="The results contain no objective"):
        get_objective(results)


def test_get_objective_raises_when_nan():
    results = DummyResults(solver=pd.Series({"objective": float("nan")}))
    with pytest.raises(ValueError, match="The results contain no objective"):
        get_objective(results)


def test_get_objective_raises_when_none():
    results = DummyResults(solver=pd.Series({"objective": None}))
    with pytest.raises(ValueError, match="The results contain no objective"):
        get_objective(results)


def test_get_objective_raises_when_unconvertible():
    results = DummyResults(solver=pd.Series({"objective": "abc"}))
    with pytest.raises(ValueError, match="The results contain no objective"):
        get_objective(results)


def test_lcoe_uses_total_cost():
    bus = CarrierBus(name="bus")
    demand = Demand(name="demand_el", bus_in=bus, input_timeseries=[0])
    es = DummyES([bus, demand])
    flows = pd.DataFrame(
        [[100.0]], columns=pd.MultiIndex.from_tuples([(bus, demand)])
    )
    results = DummyResults(
        data={"flow": flows, "eesyplan": {"total_cost": 50.0}}
    )
    LCOE(results, es)
    assert results["eesyplan"]["lcoe"] == 0.5
    assert len(results["eesyplan"]["lcoe_considered_flows"]) == 1


def test_lcoe_requires_total_cost():
    bus = CarrierBus(name="bus")
    demand = Demand(name="demand_el", bus_in=bus, input_timeseries=[0])
    es = DummyES([bus, demand])
    flows = pd.DataFrame(
        [[100.0]], columns=pd.MultiIndex.from_tuples([(bus, demand)])
    )
    results = DummyResults(data={"flow": flows})
    with pytest.raises(KeyError, match="total_cost"):
        LCOE(results, es)


def test_print_results_with_objective(capsys):
    results = DummyResults(
        data={
            "flow": pd.DataFrame(
                [[1.0]], columns=pd.MultiIndex.from_tuples([(("a",), ("b",))])
            )
        },
        solver=pd.Series(
            {
                "objective": "12345.67",
                "solver": "cbc",
                "termination_condition": "optimal",
            }
        ),
    )
    results.timeindex = pd.date_range("2012-01-01", periods=1)
    print_results(results)
    out = capsys.readouterr().out
    assert "objective      : 12345.67" in out
    assert "solver         : cbc (optimal)" in out


def test_print_results_without_objective(capsys):
    results = DummyResults(data={})
    results.timeindex = pd.DatetimeIndex([])
    print_results(results)
    out = capsys.readouterr().out
    assert "objective      : not available" in out


def test_normalize_imported_results_no_longer_sets_placeholder():
    results = DummyResults()
    normalize_imported_results(results)
    assert "objective" not in results.keys()


def test_normalize_imported_results_fixes_variable_costs():
    # Create a DataFrame with string representations
    costs = pd.DataFrame(
        [["[1.0, 2.0]"]], columns=pd.MultiIndex.from_tuples([(("a",), ("b",))])
    )
    results = DummyResults(data={"variable_costs": costs})
    normalize_imported_results(results)
    # Should be converted to numeric
    assert results["variable_costs"].iloc[0, 0] == 1.0
