"""Tests for oemof.eesyplan.postprocessing.KPIs and print_results."""

import logging
import warnings
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from oemof.eesyplan import CarrierBus
from oemof.eesyplan import Demand
from oemof.eesyplan import HeatDemand
from oemof.eesyplan import Project
from oemof.eesyplan.postprocessing import KPIs
from oemof.eesyplan.postprocessing.print_results import _format_cost
from oemof.eesyplan.postprocessing.print_results import _print_cost_table
from oemof.eesyplan.postprocessing.print_results import print_results
from oemof.solph.components import Source

# ---------------------------------------------------------------------------
# Stand-ins and helpers
# ---------------------------------------------------------------------------


class DummyResults:
    """Minimal results object with a ``_data`` dict and a solver summary."""

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
    """Top-level node stand-in; keyword arguments become attributes."""

    def __init__(self, label, **attrs):
        self.label = label
        self.parent = None
        for key, value in attrs.items():
            setattr(self, key, value)


class DummyES:
    """Minimal energy system."""

    def __init__(self, nodes):
        self.nodes = nodes


class SlotES:
    """Energy system that does not accept new attributes."""

    __slots__ = ("nodes",)

    def __init__(self, nodes):
        self.nodes = nodes


class ItemStore:
    """Supports only item access, like a plain mapping."""

    def __init__(self, data=None):
        self.store = dict(data or {})

    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value):
        self.store[key] = value


class NoneStore(ItemStore):
    """Item store that returns ``None`` for missing keys."""

    def __getitem__(self, key):
        return self.store.get(key)


def _scenario(objective=100.0):
    """Small solved scenario: wind -> bus -> demand."""
    bus = CarrierBus(name="bus")
    demand = Demand(name="demand_el", bus_in=bus, input_timeseries=[0])
    wind = Source(label="wind", outputs={bus: None})
    wind.renewable_asset = True
    wind.capex_spec = 5.0
    wind.opex_spec = 1.0
    es = DummyES([bus, demand, wind])
    flows = pd.DataFrame(
        [[100.0, 100.0]],
        columns=pd.MultiIndex.from_tuples([(wind, bus), (bus, demand)]),
    )
    results = DummyResults(
        data={
            "flow": flows,
            "invest": pd.DataFrame([[10.0]], columns=["wind"]),
            "investment_costs": pd.DataFrame([[20.0]], columns=["wind"]),
            "variable_costs": pd.DataFrame(
                [[5.0]], columns=pd.MultiIndex.from_tuples([(wind, bus)])
            ),
        },
        solver=pd.Series({"objective": objective}),
    )
    return results, es


def _optimised_data(label, owner=None, bus=None):
    """Result data of one optimised component.

    The capacity is 10 and the model's annual cost is 20.  Variable costs
    of 5 are added if ``owner`` and ``bus`` are given.
    """
    data = {
        "invest": pd.DataFrame([[10.0]], columns=[(label,)]),
        "investment_costs": pd.DataFrame([[20.0]], columns=[(label,)]),
    }
    if owner is not None:
        data["variable_costs"] = pd.DataFrame(
            [[5.0]], columns=pd.MultiIndex.from_tuples([(owner, bus)])
        )
    return data


def _project(economic_period=20, discount_factor=0.0):
    return Project(
        "p",
        tax=0.0,
        discount_factor=discount_factor,
        economic_period=economic_period,
    )


# ---------------------------------------------------------------------------
# compare_KPIs / format_KPIs
# ---------------------------------------------------------------------------


def test_compare_kpis_two_arguments():
    results, es = _scenario()

    table = KPIs.compare_KPIs(results, es, name="Base")

    assert list(table.columns) == ["Base"]
    assert table.index.name == "KPI"
    assert table.loc["Total investment costs (year 0) [€]", "Base"] == (
        pytest.approx(50.0)
    )
    assert table.loc["Total yearly fix costs [€/yr]", "Base"] == (
        pytest.approx(10.0)
    )
    dispatch = "Total yearly dispatch costs (including energy costs) [€/yr]"
    assert table.loc[dispatch, "Base"] == pytest.approx(5.0)
    assert table.loc["LCOE [ct/kWh]", "Base"] == pytest.approx(100.0)
    assert table.loc["Share of renewables [%]", "Base"] == pytest.approx(100.0)


def test_compare_kpis_single_pair_uses_default_name():
    table = KPIs.compare_KPIs(_scenario())

    assert list(table.columns) == ["Scenario"]


def test_compare_kpis_dict_with_two_scenarios():
    table = KPIs.compare_KPIs({"a": _scenario(100.0), "b": _scenario(200.0)})

    assert list(table.columns) == ["a", "b"]
    assert table.loc["LCOE [ct/kWh]", "a"] == pytest.approx(100.0)
    assert table.loc["LCOE [ct/kWh]", "b"] == pytest.approx(200.0)


def test_compare_kpis_validates_input():
    with pytest.raises(ValueError, match="at least one scenario"):
        KPIs.compare_KPIs({})

    results, _ = _scenario()
    with pytest.raises(ValueError, match=r"\(results, es\) pair"):
        KPIs.compare_KPIs({"x": (results,)})


def test_format_kpis_uses_one_decimal_and_space_separator():
    table = pd.DataFrame({"Scenario": [1234567.891]}, index=["KPI"])

    assert "1 234 567.9" in KPIs.format_KPIs(table)


# ---------------------------------------------------------------------------
# _eesyplan_kpis and _store_result
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("store_class", [ItemStore, NoneStore])
def test_eesyplan_kpis_item_access_creates_namespace(store_class):
    results = store_class()

    kpis = KPIs._eesyplan_kpis(results)

    assert kpis == {}
    assert results.store[KPIs.EESYPLAN_KEY] is kpis


def test_eesyplan_kpis_item_access_keeps_existing_namespace():
    existing = {"lcoe": 1.0}
    results = ItemStore({KPIs.EESYPLAN_KEY: existing})

    assert KPIs._eesyplan_kpis(results) is existing


def test_eesyplan_kpis_attribute_fallback():
    results = SimpleNamespace()

    kpis = KPIs._eesyplan_kpis(results)
    KPIs._store_result(results, "lcoe", 2.0)

    assert getattr(results, KPIs.EESYPLAN_KEY) is kpis
    assert KPIs._eesyplan_kpis(results) is kpis
    assert kpis == {"lcoe": 2.0}


# ---------------------------------------------------------------------------
# Solver summary and objective
# ---------------------------------------------------------------------------


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

    assert KPIs._solver_value(results, "objective") == 123.45
    assert KPIs._solver_value(results, "solver") == "cbc"
    assert KPIs._solver_value(results, "termination_condition") == "optimal"
    assert KPIs._solver_value(results, "missing") is None


def test_solver_value_from_dict_like():
    results = DummyResults(solver={"objective": 10, "solver": "glpk"})

    assert KPIs._solver_value(results, "objective") == 10
    assert KPIs._solver_value(results, "solver") == "glpk"


def test_solver_value_from_object():
    results = DummyResults(
        solver=SimpleNamespace(objective=5.5, solver="highs")
    )

    assert KPIs._solver_value(results, "objective") == 5.5
    assert KPIs._solver_value(results, "solver") == "highs"


def test_solver_value_no_solver():
    assert KPIs._solver_value(DummyResults(), "objective") is None


def test_solver_value_object_without_attribute():
    class Solver:
        pass

    results = DummyResults(solver=Solver())

    assert KPIs._solver_value(results, "objective") is None


def test_solver_value_dict_with_failing_get():
    class FailingGet(dict):
        def get(self, *args, **kwargs):
            raise AttributeError

    results = DummyResults(solver=FailingGet({"objective": 1}))

    # ``get`` fails, so the value is read by item access instead.
    assert KPIs._solver_value(results, "objective") == 1


def test_solver_value_attribute_that_fails_on_second_access():
    class Flaky:
        def __init__(self):
            self.count = 0

        @property
        def objective(self):
            self.count += 1
            if self.count > 1:
                raise RuntimeError("second access fails")
            return 1.0

    results = DummyResults(solver=Flaky())

    assert KPIs._solver_value(results, "objective") is None


def test_get_objective_from_solver_series_string():
    results = DummyResults(
        solver=pd.Series({"objective": "62137253.933979616"})
    )

    assert KPIs.get_objective(results) == 62137253.933979616


def test_get_objective_from_solver_series_float():
    results = DummyResults(solver=pd.Series({"objective": 1234.56}))

    assert KPIs.get_objective(results) == 1234.56


def test_get_objective_numpy_float():
    results = DummyResults(solver=pd.Series({"objective": np.float64(123.45)}))

    assert KPIs.get_objective(results) == 123.45


def test_get_objective_int():
    results = DummyResults(solver=pd.Series({"objective": 100}))

    assert KPIs.get_objective(results) == 100.0


def test_get_objective_from_solver_dict():
    results = DummyResults(solver={"objective": "100.0"})

    assert KPIs.get_objective(results) == 100.0


def test_get_objective_from_solver_namespace():
    results = DummyResults(solver=SimpleNamespace(objective=42))

    assert KPIs.get_objective(results) == 42.0


def test_get_objective_legacy_key():
    results = DummyResults(data={"objective": 20000.0})

    assert KPIs.get_objective(results) == 20000.0


def test_get_objective_legacy_key_string():
    results = DummyResults(data={"objective": "555.5"})

    assert KPIs.get_objective(results) == 555.5


def test_get_objective_solver_without_objective_uses_legacy_key():
    results = DummyResults(
        data={"objective": 777}, solver=pd.Series({"solver": "cbc"})
    )

    assert KPIs.get_objective(results) == 777.0


def test_get_objective_solver_dict_without_objective_uses_legacy_key():
    results = DummyResults(data={"objective": "888"}, solver={"solver": "cbc"})

    assert KPIs.get_objective(results) == 888.0


@pytest.mark.parametrize(
    "solver",
    [
        None,
        pd.Series({"objective": float("nan")}),
        pd.Series({"objective": None}),
        pd.Series({"objective": "abc"}),
    ],
    ids=["missing", "nan", "none", "unconvertible"],
)
def test_get_objective_raises_without_valid_objective(solver):
    results = DummyResults(solver=solver)

    with pytest.raises(ValueError, match="The results contain no objective"):
        KPIs.get_objective(results)


# ---------------------------------------------------------------------------
# LCOE
# ---------------------------------------------------------------------------


def test_lcoe_uses_total_cost():
    bus = CarrierBus(name="bus")
    demand = Demand(name="demand_el", bus_in=bus, input_timeseries=[0])
    flows = pd.DataFrame(
        [[100.0]], columns=pd.MultiIndex.from_tuples([(bus, demand)])
    )
    results = DummyResults(
        data={"flow": flows, "eesyplan": {"total_cost": 50.0}}
    )

    KPIs.LCOE(results, DummyES([bus, demand]))

    assert results["eesyplan"]["lcoe"] == 0.5
    assert len(results["eesyplan"]["lcoe_considered_flows"]) == 1


def test_lcoe_requires_total_cost():
    bus = CarrierBus(name="bus")
    demand = Demand(name="demand_el", bus_in=bus, input_timeseries=[0])
    flows = pd.DataFrame(
        [[100.0]], columns=pd.MultiIndex.from_tuples([(bus, demand)])
    )
    results = DummyResults(data={"flow": flows})

    with pytest.raises(KeyError, match="total_cost"):
        KPIs.LCOE(results, DummyES([bus, demand]))


def test_lcoe_is_zero_without_demand_flows():
    bus = CarrierBus(name="bus")
    demand = Demand(name="demand_el", bus_in=bus, input_timeseries=[0])
    source = Source(label="wind", outputs={bus: None})
    flows = pd.DataFrame(
        [[10.0]], columns=pd.MultiIndex.from_tuples([(source, bus)])
    )
    results = DummyResults(
        data={"flow": flows, "eesyplan": {"total_cost": 10.0}}
    )

    KPIs.LCOE(results, DummyES([bus, demand, source]))

    assert results["eesyplan"]["lcoe"] == 0
    assert results["eesyplan"]["lcoe_considered_flows"] == []


# ---------------------------------------------------------------------------
# Labels and result keys
# ---------------------------------------------------------------------------


def test_clean_label_plain():
    assert KPIs.clean_label("Strom_bus") == "Strom_bus"


def test_clean_label_tuple_string():
    result = KPIs.clean_label("('feedin_converter', 'Stromversorger')")

    assert result == "feedin_converter | Stromversorger"


def test_clean_label_with_carrier_removed():
    result = KPIs.clean_label("<CarrierBus 'Wärme_bus', carrier='Heat'>")

    assert result == "Wärme_bus"


def test_clean_label_tokens():
    result = KPIs.clean_label("<...HeatPump: 'Luft-Wärmepumpe'>")

    assert result == "Luft-Wärmepumpe"


def test_edge_label():
    assert KPIs.edge_label((("src",), ("dst",))) == ("src", "dst")


def test_norm_label():
    assert KPIs._norm_label(("a", "b")) == "a | b"
    assert KPIs._norm_label("test") == "test"


def test_result_keys():
    results = DummyResults(
        data={
            "objective": 1,
            "Problem": 2,
            "Solution": 3,
            "Solver": 4,
            "flow": pd.DataFrame(),
        }
    )

    assert KPIs.result_keys(results) == ["flow", "objective"]


def test_demand_labels():
    bus = CarrierBus(name="bus")
    demand = Demand(name="demand_el", bus_in=bus, input_timeseries=[0])
    heat_demand = HeatDemand(
        name="demand_heat", bus_in_heat=bus, input_timeseries=[0]
    )

    labels = KPIs.demand_labels(DummyES([bus, demand, heat_demand]))

    assert demand.label in labels
    assert heat_demand.label in labels
    assert bus.label not in labels


# ---------------------------------------------------------------------------
# Renewable fraction and renewable share
# ---------------------------------------------------------------------------


def test_renewable_fraction_none():
    assert KPIs._renewable_fraction(DummyNode("n")) == 0.0


def test_renewable_fraction_asset_true():
    node = DummyNode("n", renewable_asset=True)

    assert KPIs._renewable_fraction(node) == 1.0


def test_renewable_fraction_asset_false():
    node = DummyNode("n", renewable_asset=False)

    assert KPIs._renewable_fraction(node) == 0.0


def test_renewable_fraction_share():
    node = DummyNode("n", renewable_share=0.4)

    assert KPIs._renewable_fraction(node) == 0.4


def test_renewable_fraction_inherits():
    parent = DummyNode("parent", renewable_share=0.6)
    child = DummyNode("child")
    child.parent = parent

    assert KPIs._renewable_fraction(child) == 0.6


def test_renewable_share():
    bus = CarrierBus(name="bus")
    src = Source(label="wind", outputs={bus: None})
    src.renewable_asset = True
    flows = pd.DataFrame(
        [[100.0]], columns=pd.MultiIndex.from_tuples([(src, bus)])
    )
    results = DummyResults(data={"flow": flows})

    KPIs.renewable_share(results, DummyES([bus, src]))

    assert results["eesyplan"]["renewable_share"] == 1.0


def test_renewable_share_mixed():
    bus = CarrierBus(name="bus")
    wind = Source(label="wind", outputs={bus: None})
    wind.renewable_asset = True
    gas = Source(label="gas", outputs={bus: None})
    gas.renewable_asset = False
    flows = pd.DataFrame(
        [[60.0, 40.0]],
        columns=pd.MultiIndex.from_tuples([(wind, bus), (gas, bus)]),
    )
    results = DummyResults(data={"flow": flows})

    KPIs.renewable_share(results, DummyES([bus, wind, gas]))

    assert results["eesyplan"]["renewable_share"] == 0.6


def test_renewable_share_zero_total():
    bus = CarrierBus(name="bus")
    src = Source(label="wind", outputs={bus: None})
    flows = pd.DataFrame(
        [[0.0]], columns=pd.MultiIndex.from_tuples([(src, bus)])
    )
    results = DummyResults(data={"flow": flows})

    # A division by zero gives nan (with a numpy warning).
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        KPIs.renewable_share(results, DummyES([bus, src]))

    result = results["eesyplan"]["renewable_share"]
    assert pd.isna(result) or result == 0


# ---------------------------------------------------------------------------
# Owners
# ---------------------------------------------------------------------------


def test_top_level_node():
    parent = DummyNode("parent")
    child = DummyNode("child")
    child.parent = parent

    assert KPIs._top_level_node(child) is parent
    assert KPIs._top_level_node(parent) is parent


def test_owner_map():
    bus = CarrierBus(name="bus")
    parent = DummyNode("parent")
    child = DummyNode("child")
    child.parent = parent

    owners = KPIs._owner_map(DummyES([bus, parent, child]))

    assert owners[KPIs._norm_label(child.label)] is parent


def test_is_neutral():
    bus = CarrierBus(name="bus")
    demand = Demand(name="d", bus_in=bus, input_timeseries=[0])

    assert KPIs._is_neutral(bus) is True
    assert KPIs._is_neutral(demand) is True
    assert KPIs._is_neutral(DummyNode("owner")) is False


def test_owner_of_parts():
    bus = CarrierBus(name="bus")
    owner = DummyNode("owner")
    bus_label = KPIs._norm_label(bus.label)
    owners = {bus_label: bus, "owner": owner}

    assert KPIs._owner_of_parts(["owner", bus_label], owners) is owner


def test_owner_of_parts_only_neutral():
    bus = CarrierBus(name="bus")
    bus_label = KPIs._norm_label(bus.label)

    assert KPIs._owner_of_parts([bus_label], {bus_label: bus}) is bus


def test_owner_of_parts_without_match_and_with_neutral_nodes():
    bus = CarrierBus(name="bus")
    owner = DummyNode("owner")
    owners = {"bus": bus, "owner": owner}

    assert KPIs._owner_of_parts(["ghost"], owners) is None
    assert KPIs._owner_of_parts(["ghost", "owner"], owners) is owner
    assert KPIs._owner_of_parts(["ghost", "bus"], owners) is bus
    assert KPIs._owner_of_parts(["bus", "owner"], owners) is owner


def test_edge_owner():
    bus = CarrierBus(name="bus")
    owner = DummyNode("owner")
    owners = {"bus": bus, "owner": owner}

    # The neutral bus is skipped in favour of the other end.
    assert KPIs._edge_owner(("bus", "owner"), owners) is owner


def test_edge_owner_prefers_non_neutral_node():
    bus = CarrierBus(name="bus")
    owner = DummyNode("owner")
    owners = {"bus": bus, "owner": owner}

    assert KPIs._edge_owner(("owner", "bus"), owners) is owner
    assert KPIs._edge_owner(("bus", "owner"), owners) is owner
    assert KPIs._edge_owner(("bus", "ghost"), owners) is bus
    assert KPIs._edge_owner(("ghost", "other"), owners) is None


def test_column_parts():
    assert KPIs._column_parts(("a | b",)) == ["a", "b"]


# ---------------------------------------------------------------------------
# _component_cost_data
# ---------------------------------------------------------------------------


def test_component_cost_data():
    bus = CarrierBus(name="bus")
    owner = DummyNode("owner", opex_spec=1.0)
    results = DummyResults(data=_optimised_data("owner", owner, bus))

    _, capacity, investment_cost, _, _, _ = KPIs._component_cost_data(
        results, DummyES([bus, owner])
    )

    assert capacity == {owner: 10.0}
    assert investment_cost == {owner: 20.0}


def test_component_cost_data_skips_unknown_zero_and_duplicate_columns():
    owner = DummyNode("owner", opex_spec=1.0)
    results = DummyResults(
        data={
            "invest": pd.DataFrame(
                [[0.0, 3.0, 7.0, 9.0]],
                columns=["owner", "ghost", "owner", "owner"],
            ),
            "investment_costs": pd.DataFrame(
                [[1.0, 5.0, 6.0]], columns=["ghost", "owner", "owner"]
            ),
        }
    )

    components, capacity, investment_cost, variable, _, _ = (
        KPIs._component_cost_data(results, DummyES([owner]))
    )

    assert components == [owner]
    assert capacity == {owner: 7.0}
    assert investment_cost == {owner: 5.0}
    assert variable == {}


def test_component_cost_data_variable_costs_unknown_owner_and_text():
    owner = DummyNode("owner")
    costs = pd.DataFrame(
        [["[0.0]", "[0.0]"], ["[0.0]", "[0.0]"]],
        columns=pd.MultiIndex.from_tuples(
            [("owner", "x"), ("ghost", "other")]
        ),
    )
    results = DummyResults(data={"variable_costs": costs})

    _, _, _, variable, _, _ = KPIs._component_cost_data(
        results, DummyES([owner])
    )

    # Text cannot be summed: the owner counts with 0, unknown owners vanish.
    assert variable == {owner: 0.0}


# ---------------------------------------------------------------------------
# _fix_cost_data
# ---------------------------------------------------------------------------


def test_fix_cost_data_annualizes_with_project():
    project = _project()
    node = DummyNode(
        "n",
        investment_fix_cost=100.0,
        annual_fix_cost=5.0,
        lifetime=10,
        project_data=project,
    )

    fix_investment_ann, fix_annual = KPIs._fix_cost_data(DummyES([node]), {})

    assert fix_annual[node] == 5.0
    assert fix_investment_ann[node] == project.calculate_annuity(100.0, 10)


def test_fix_cost_data_uses_replacement_timing_for_installed():
    project = _project(discount_factor=0.05)
    node = DummyNode(
        "n",
        investment_fix_cost=100.0,
        installed_capacity=5.0,
        lifetime=10,
        age_installed=4,
        project_data=project,
    )

    fix_investment_ann, _ = KPIs._fix_cost_data(DummyES([node]), {})

    assert fix_investment_ann[node] == project.calculate_annuity(
        100.0, 10, year_of_investment=6
    )


def test_fix_cost_data_lifetime_fallback_to_economic_period(caplog):
    project = _project(economic_period=15)
    node = DummyNode("n", investment_fix_cost=100.0, project_data=project)

    with caplog.at_level(logging.WARNING):
        fix_investment_ann, _ = KPIs._fix_cost_data(DummyES([node]), {})

    assert "has no lifetime" in caplog.text
    assert "has no age_installed" in caplog.text
    assert fix_investment_ann[node] == project.calculate_annuity(100.0, 15)


def test_fix_cost_data_fallback_without_project_and_lifetime(caplog):
    node = DummyNode("n", investment_fix_cost=100.0)

    with caplog.at_level(logging.WARNING):
        fix_investment_ann, _ = KPIs._fix_cost_data(DummyES([node]), {})

    assert "has no lifetime" in caplog.text
    assert "has no project data" in caplog.text
    # The lifetime falls back to 20, the annuity is calculated linearly.
    assert fix_investment_ann[node] == pytest.approx(5.0)


def test_fix_cost_data_warns_on_zero_capacity(caplog):
    node = DummyNode("n", annual_fix_cost=5.0)

    with caplog.at_level(logging.WARNING):
        fix_investment_ann, fix_annual = KPIs._fix_cost_data(
            DummyES([node]), {}
        )

    assert "has no capacity" in caplog.text
    assert fix_annual[node] == 5.0
    assert fix_investment_ann == {}


def test_fix_cost_data_warns_only_once(caplog):
    es = DummyES([DummyNode("n", annual_fix_cost=5.0)])

    with caplog.at_level(logging.WARNING):
        KPIs._fix_cost_data(es, {})
        KPIs._fix_cost_data(es, {})

    assert caplog.text.count("has no capacity") == 1


def test_fix_cost_data_without_attribute_assignment(caplog):
    node = DummyNode("n", annual_fix_cost=5.0)
    es = SlotES([node])

    with caplog.at_level(logging.DEBUG):
        _, fix_annual = KPIs._fix_cost_data(es, {})
        KPIs._fix_cost_data(es, {})

    assert fix_annual == {node: 5.0}
    assert "does not accept attributes" in caplog.text
    # The result cannot be cached, so the warning is logged again.
    assert caplog.text.count("has no capacity") == 2


# ---------------------------------------------------------------------------
# _effective_capacity and _component_costs
# ---------------------------------------------------------------------------


def test_effective_capacity():
    node = DummyNode("n", installed_capacity=10)
    optimised = DummyNode("n2", installed_capacity=10)

    assert KPIs._effective_capacity(node, {}) == 10.0
    assert KPIs._effective_capacity(optimised, {optimised: 5.0}) == 5.0


def test_component_costs_optimized():
    node = DummyNode("n", opex_spec=1.0)

    capex, opex = KPIs._component_costs(node, {node: 10.0}, {node: 20.0})

    assert opex == 10.0
    assert capex == 10.0


def test_component_costs_installed():
    node = DummyNode(
        "n",
        installed_capacity=10,
        opex_spec=1.0,
        installed_capex_spec_annualized=2.0,
    )

    capex, opex = KPIs._component_costs(node, {}, {})

    assert opex == 10.0
    assert capex == 20.0


def test_component_costs_adds_fix_costs():
    node = DummyNode("n", opex_spec=1.0)

    capex, opex = KPIs._component_costs(
        node, {node: 10.0}, {node: 20.0}, {node: 7.0}, {node: 3.0}
    )

    # The annuity is reconstructed as investment_costs - opex, so the flat
    # fix costs must not distort that reconstruction.
    assert capex == 17.0
    assert opex == 13.0


@pytest.mark.parametrize("attribute", ["project_data", "_project_data"])
def test_component_costs_installed_annualizes_with_project(attribute):
    project = _project()
    node = DummyNode(
        "n",
        installed_capacity=10.0,
        opex_spec=1.0,
        capex_spec=100.0,
        lifetime=10,
        age_installed=2,
        **{attribute: project},
    )

    capex, opex = KPIs._component_costs(node, {}, {})

    expected = project.calculate_annuity(100.0, 10, year_of_investment=8)
    assert capex == pytest.approx(expected * 10.0)
    assert opex == pytest.approx(10.0)


def test_component_costs_installed_without_project_data():
    node = DummyNode("n", installed_capacity=10.0, opex_spec=1.0)

    capex, opex = KPIs._component_costs(node, {}, {})

    assert capex == 0.0
    assert opex == 10.0


# ---------------------------------------------------------------------------
# Totals
# ---------------------------------------------------------------------------


def test_total_component_opex_adds_annual_fix_cost():
    owner = DummyNode("owner", opex_spec=2.0, annual_fix_cost=3.0)
    results = DummyResults(
        data={"invest": pd.DataFrame([[10.0]], columns=["owner"])}
    )

    assert KPIs._total_component_opex(results, DummyES([owner])) == (
        pytest.approx(23.0)
    )


def test_total_variable_costs():
    assert KPIs._total_variable_costs(DummyResults()) == 0.0

    costs = pd.DataFrame([[1.0, 2.0], [3.0, 4.0]])
    results = DummyResults(data={"variable_costs": costs})

    assert KPIs._total_variable_costs(results) == pytest.approx(10.0)


def test_additional_installed_costs_installed_and_optimised():
    installed = DummyNode(
        "installed",
        installed_capacity=10.0,
        opex_spec=1.0,
        installed_capex_spec_annualized=2.0,
    )
    optimised = DummyNode("opt", annual_fix_cost=4.0)
    results = DummyResults(
        data={"invest": pd.DataFrame([[5.0]], columns=["opt"])}
    )

    costs = KPIs._additional_installed_costs(
        results, DummyES([installed, optimised])
    )

    # Installed: 2 * 10 capex + 1 * 10 opex. Optimised: only the fix cost.
    assert costs == pytest.approx(34.0)


def test_total_cost():
    bus = CarrierBus(name="bus")
    owner = DummyNode("owner_node", opex_spec=1.0, capex_spec=5.0)
    results = DummyResults(
        data=_optimised_data("owner_node", owner, bus),
        solver=pd.Series({"objective": 100.0}),
    )

    KPIs.total_cost(results, DummyES([bus, owner]))

    assert results["eesyplan"]["total_cost"] == 100.0


def test_total_cost_adds_installed_fixed_costs():
    bus = CarrierBus(name="bus")
    owner = DummyNode(
        "owner_node",
        installed_capacity=10.0,
        opex_spec=1.0,
        installed_capex_spec_annualized=2.0,
    )
    results = DummyResults(data={}, solver=pd.Series({"objective": 100.0}))

    KPIs.total_cost(results, DummyES([bus, owner]))

    # 100 objective + 20 replacement capex + 10 opex
    assert results["eesyplan"]["total_cost"] == 130.0


def test_total_cost_includes_fix_costs():
    bus = CarrierBus(name="bus")
    owner = DummyNode(
        "owner_node",
        opex_spec=1.0,
        capex_spec=5.0,
        lifetime=10,
        investment_fix_cost=100.0,
        annual_fix_cost=3.0,
        project_data=_project(),
    )
    results = DummyResults(
        data=_optimised_data("owner_node"),
        solver=pd.Series({"objective": 100.0}),
    )

    KPIs.total_cost(results, DummyES([bus, owner]))

    # Objective 100 + annualized fix investment 100/10 + annual fix 3.
    assert results["eesyplan"]["total_cost"] == pytest.approx(113.0)


def test_total_cost_adds_fix_costs_of_installed_component():
    bus = CarrierBus(name="bus")
    owner = DummyNode(
        "owner_node",
        installed_capacity=10.0,
        installed_capex_spec_annualized=2.0,
        opex_spec=1.0,
        lifetime=10,
        age_installed=2,
        investment_fix_cost=100.0,
        annual_fix_cost=3.0,
        project_data=_project(),
    )
    results = DummyResults(data={}, solver=pd.Series({"objective": 100.0}))

    KPIs.total_cost(results, DummyES([bus, owner]))

    # 100 objective + 20 replacement capex + 10 opex
    # + 10 fix investment annuity + 3 annual fix cost
    assert results["eesyplan"]["total_cost"] == pytest.approx(143.0)


def test_calculate_all_kpis():
    bus = CarrierBus(name="bus")
    demand = Demand(name="demand_el", bus_in=bus, input_timeseries=[0])
    source = Source(label="wind", outputs={bus: None})
    source.renewable_asset = True
    owner = DummyNode("owner_node", opex_spec=1.0, capex_spec=5.0)
    flows = pd.DataFrame(
        [[100.0, 100.0, 0.0]],
        columns=pd.MultiIndex.from_tuples(
            [(source, bus), (bus, demand), (owner, bus)]
        ),
    )
    results = DummyResults(
        data={"flow": flows}, solver=pd.Series({"objective": 50.0})
    )

    KPIs.calculate_all_kpis(
        results, DummyES([bus, demand, source, owner]), project_duration=10
    )

    kpis = results["eesyplan"]
    assert kpis["total_cost"] == 50.0
    assert kpis["lcoe"] == 0.5
    assert kpis["renewable_share"] == 1.0
    assert "yearly_project_costs" in kpis
    assert "project_cost_table" in kpis


# ---------------------------------------------------------------------------
# Project duration
# ---------------------------------------------------------------------------


def test_economic_period_sources():
    project = _project(economic_period=12)
    node_project = DummyNode("a", project_data=project)
    node_private = DummyNode("b", _project_data=project)
    es_with_project = DummyES([])
    es_with_project.project_data = project

    assert KPIs._economic_period(DummyES([])) is None
    assert KPIs._economic_period(DummyES([node_project])) == 12
    assert KPIs._economic_period(DummyES([node_private])) == 12
    assert KPIs._economic_period(es_with_project) == 12


def test_project_duration_explicit_and_fallback(caplog):
    es = DummyES([])

    assert KPIs._project_duration(es, project_duration=7) == 7
    with caplog.at_level(logging.WARNING):
        assert KPIs._project_duration(es) == 20
    assert "Falling back to a project duration of 20" in caplog.text


# ---------------------------------------------------------------------------
# Cost tables
# ---------------------------------------------------------------------------


def test_cost_table():
    rows = [{"Component": "a", "cost1": 10.0, "cost2": 5.0}]

    table = KPIs._cost_table(rows, ["cost1", "cost2"])

    assert list(table["Component"]) == ["a", "total"]
    total_row = table[table["Component"] == "total"].iloc[0]
    assert total_row["total"] == pytest.approx(15.0)


def test_cost_table_filters_zeros():
    rows = [{"Component": "a", "cost1": 0.0}]

    table = KPIs._cost_table(rows, ["cost1"])

    # Components without cost are dropped, only the total row is left.
    assert list(table["Component"]) == ["total"]


def test_yearly_project_costs():
    bus = CarrierBus(name="bus")
    owner = DummyNode("owner_node", opex_spec=1.0)
    results = DummyResults(data=_optimised_data("owner_node", owner, bus))

    KPIs.yearly_project_costs(results, DummyES([bus, owner]))

    table = results["eesyplan"]["yearly_project_costs"]
    row = table[table["Component"] == "owner_node"].iloc[0]
    assert "total" in table.columns
    # Model annuity 20 - opex 10, and opex 1 * 10.
    assert row["Annualized investment cost"] == pytest.approx(10.0)
    assert row["Fix operational costs"] == pytest.approx(10.0)


def test_yearly_project_costs_with_fix_costs():
    bus = CarrierBus(name="bus")
    owner = DummyNode(
        "owner_node",
        opex_spec=1.0,
        lifetime=10,
        investment_fix_cost=100.0,
        annual_fix_cost=5.0,
        project_data=_project(),
    )
    results = DummyResults(data=_optimised_data("owner_node"))

    KPIs.yearly_project_costs(results, DummyES([bus, owner]))

    table = results["eesyplan"]["yearly_project_costs"]
    row = table[table["Component"] == "owner_node"].iloc[0]
    # Model annuity 10 (20 - 10 opex) + fix annuity 100/10.
    assert row["Annualized investment cost"] == pytest.approx(20.0)
    # Opex 10 + annual fix 5.
    assert row["Fix operational costs"] == pytest.approx(15.0)


def test_project_cost_table():
    bus = CarrierBus(name="bus")
    owner = DummyNode("owner_node", opex_spec=1.0, capex_spec=5.0)
    results = DummyResults(data=_optimised_data("owner_node", owner, bus))

    KPIs.project_cost_table(
        results, DummyES([bus, owner]), project_duration=20
    )

    table = results["eesyplan"]["project_cost_table"]
    row = table[table["Component"] == "owner_node"].iloc[0]
    year0 = "Investment cost in year 0 (not including reinvestment)"
    # capex_spec 5 * capacity 10.
    assert row[year0] == pytest.approx(50.0)
    # Annuity 10 * 20 years - year 0 investment 50.
    assert row["Reinvestment cost over the full project"] == (
        pytest.approx(150.0)
    )
    # Opex 10 * 20 years.
    assert row["Fix operational costs over project duration"] == (
        pytest.approx(200.0)
    )


def test_project_cost_table_with_fix_costs():
    bus = CarrierBus(name="bus")
    owner = DummyNode(
        "owner_node",
        opex_spec=1.0,
        capex_spec=5.0,
        lifetime=10,
        investment_fix_cost=100.0,
        annual_fix_cost=5.0,
        project_data=_project(),
    )
    results = DummyResults(data=_optimised_data("owner_node"))

    KPIs.project_cost_table(
        results, DummyES([bus, owner]), project_duration=20
    )

    table = results["eesyplan"]["project_cost_table"]
    row = table[table["Component"] == "owner_node"].iloc[0]
    # capex_spec * capacity 5 * 10 + fix investment 100 in year 0.
    assert row["Investment cost in year 0 (not including reinvestment)"] == (
        pytest.approx(150.0)
    )
    # Annualized investment 20 * 20 years - year 0 investment 150.
    assert row["Reinvestment cost over the full project"] == (
        pytest.approx(250.0)
    )
    # (Opex 10 + annual fix 5) * 20 years.
    assert row["Fix operational costs over project duration"] == (
        pytest.approx(300.0)
    )


def test_project_cost_table_installed_without_fix_year0():
    bus = CarrierBus(name="bus")
    owner = DummyNode(
        "owner_node",
        installed_capacity=10.0,
        installed_capex_spec_annualized=2.0,
        opex_spec=1.0,
        lifetime=10,
        age_installed=2,
        investment_fix_cost=100.0,
        annual_fix_cost=3.0,
        project_data=_project(),
    )
    results = DummyResults(data={})

    KPIs.project_cost_table(
        results, DummyES([bus, owner]), project_duration=20
    )

    table = results["eesyplan"]["project_cost_table"]
    row = table[table["Component"] == "owner_node"].iloc[0]
    # Existing components paid their fix investment before the project.
    assert row["Investment cost in year 0 (not including reinvestment)"] == 0.0


# ---------------------------------------------------------------------------
# normalize_imported_results and _numeric_variable_costs
# ---------------------------------------------------------------------------


def test_numeric_variable_costs():
    result = KPIs._numeric_variable_costs(pd.DataFrame([["[1.5, 2.5]"]]))

    assert result.iloc[0, 0] == 1.5


def test_numeric_variable_costs_without_number_is_nan():
    result = KPIs._numeric_variable_costs(pd.DataFrame([["abc", 2.0]]))

    assert pd.isna(result.iloc[0, 0])
    assert result.iloc[0, 1] == 2.0


def test_normalize_imported_results_does_not_add_objective_placeholder():
    results = DummyResults()

    KPIs.normalize_imported_results(results)

    assert "objective" not in results.keys()


def test_normalize_imported_results_keeps_numeric_variable_costs():
    costs = pd.DataFrame([[1.0, 2.0], [3.0, 4.0]])
    results = DummyResults(data={"variable_costs": costs})

    KPIs.normalize_imported_results(results)

    assert results["variable_costs"].iloc[0, 0] == 1.0


def test_normalize_imported_results_empty_variable_costs():
    results = DummyResults(data={"variable_costs": pd.DataFrame()})

    # Must not raise.
    KPIs.normalize_imported_results(results)


def test_normalize_imported_results_fixes_variable_costs():
    costs = pd.DataFrame(
        [["[1.0, 2.0]"]], columns=pd.MultiIndex.from_tuples([(("a",), ("b",))])
    )
    results = DummyResults(data={"variable_costs": costs})

    KPIs.normalize_imported_results(results)

    assert results["variable_costs"].iloc[0, 0] == 1.0


# ---------------------------------------------------------------------------
# print_results
# ---------------------------------------------------------------------------


def test_print_flows(capsys):
    flows = pd.DataFrame(
        [[10.0, 0.0]],
        columns=pd.MultiIndex.from_tuples(
            [(("a",), ("b",)), (("c",), ("d",))]
        ),
    )

    print_results(DummyResults(data={"flow": flows}))

    assert "Flows" in capsys.readouterr().out


def test_print_flows_no_flow(capsys):
    print_results(DummyResults(data={}))

    assert "Flows" not in capsys.readouterr().out


def test_print_storages(capsys):
    storage = pd.DataFrame(
        [[1.0, 5.0]], columns=[("storage1",), ("storage2",)]
    )

    print_results(DummyResults(data={"storage_content": storage}))

    assert "Storage content" in capsys.readouterr().out


def test_print_storages_no_key(capsys):
    print_results(DummyResults(data={}))

    assert "Storage content" not in capsys.readouterr().out


def test_print_investments(capsys):
    invest = pd.DataFrame([[10.0, 0.0]], columns=[("comp1",), ("comp2",)])
    costs = pd.DataFrame([[5.0]], columns=[("comp1",)])

    print_results(
        DummyResults(data={"invest": invest, "investment_costs": costs})
    )

    assert "Annual equivalent periodical costs" in capsys.readouterr().out


def test_print_investments_no_invest(capsys):
    print_results(DummyResults(data={}))

    assert "Optimised capacities" not in capsys.readouterr().out


def test_print_costs(capsys):
    costs = pd.DataFrame(
        [[3.0, 0.0]],
        columns=pd.MultiIndex.from_tuples(
            [(("a",), ("b",)), (("c",), ("d",))]
        ),
    )

    print_results(DummyResults(data={"variable_costs": costs}))

    assert "Variable costs" in capsys.readouterr().out


def test_print_costs_no_key(capsys):
    print_results(DummyResults(data={}))

    assert "Variable costs" not in capsys.readouterr().out


def test_print_cost_table(capsys):
    table = pd.DataFrame([{"Component": "a", "cost1": 10.0, "total": 10.0}])

    _print_cost_table(table)

    assert "a" in capsys.readouterr().out


def test_print_cost_table_with_title(capsys):
    table = pd.DataFrame([{"Component": "a", "cost1": 10.0, "total": 10.0}])

    _print_cost_table(table, title="Test:")

    assert "Test:" in capsys.readouterr().out


def test_format_cost_non_numeric():
    assert _format_cost([1, 2], 5).strip() == "-"
    assert _format_cost(float("nan"), 5).strip() == "-"
    assert _format_cost(12.5, 8).strip() == "12.50"


def test_print_cost_table_non_numeric_cell(capsys):
    table = pd.DataFrame([{"Component": "a", "cost1": [1, 2], "total": 3.0}])

    _print_cost_table(table)

    out = capsys.readouterr().out
    assert "a" in out
    assert "-" in out


def test_print_results_full(capsys):
    results = DummyResults(
        data={
            "flow": pd.DataFrame(
                [[1.0, 2.0]],
                columns=pd.MultiIndex.from_tuples(
                    [(("a",), ("b",)), (("c",), ("d",))]
                ),
            )
        },
        solver=pd.Series(
            {
                "objective": "100.0",
                "solver": "cbc",
                "termination_condition": "optimal",
            }
        ),
    )
    results.timeindex = pd.date_range("2012-01-01", periods=1)

    print_results(results)

    out = capsys.readouterr().out
    assert "RESULTS - STRUCTURE" in out
    assert "objective" in out


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

    assert "objective      : not available" in capsys.readouterr().out


def test_print_results_solver_no_termination_condition(capsys):
    results = DummyResults(
        data={"flow": pd.DataFrame()},
        solver=pd.Series({"objective": "50.0", "solver": "cbc"}),
    )
    results.timeindex = pd.DatetimeIndex([])

    print_results(results)

    out = capsys.readouterr().out
    assert "objective      : 50.00" in out
    assert "solver         : cbc" in out


def test_print_results_solver_dict(capsys):
    results = DummyResults(
        data={"flow": pd.DataFrame()},
        solver={
            "objective": 42,
            "solver": "highs",
            "termination_condition": "optimal",
        },
    )
    results.timeindex = pd.DatetimeIndex([])

    print_results(results)

    out = capsys.readouterr().out
    assert "42.00" in out
    assert "highs (optimal)" in out


def test_print_result_structure_skips_unavailable_keys(capsys):
    class SparseResults(DummyResults):
        def keys(self):
            # oemof advertises variables without data, e.g. "invest_status".
            return set(self._data.keys()) | {"invest_status"}

    results = SparseResults(data={"flow": pd.DataFrame()})
    results.timeindex = pd.DatetimeIndex([])

    print_results(results)

    out = capsys.readouterr().out
    assert "flow" in out
    assert "invest_status" not in out
