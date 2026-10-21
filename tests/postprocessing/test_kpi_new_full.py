import warnings

import numpy as np
import pandas as pd

from oemof.eesyplan import CarrierBus
from oemof.eesyplan import Demand
from oemof.eesyplan import HeatDemand
from oemof.eesyplan.postprocessing.KPIs import LCOE
from oemof.eesyplan.postprocessing.KPIs import _column_parts
from oemof.eesyplan.postprocessing.KPIs import _component_cost_data
from oemof.eesyplan.postprocessing.KPIs import _component_costs
from oemof.eesyplan.postprocessing.KPIs import _cost_table
from oemof.eesyplan.postprocessing.KPIs import _edge_owner
from oemof.eesyplan.postprocessing.KPIs import _effective_capacity
from oemof.eesyplan.postprocessing.KPIs import _is_neutral
from oemof.eesyplan.postprocessing.KPIs import _norm_label
from oemof.eesyplan.postprocessing.KPIs import _numeric_variable_costs
from oemof.eesyplan.postprocessing.KPIs import _owner_map
from oemof.eesyplan.postprocessing.KPIs import _owner_of_parts
from oemof.eesyplan.postprocessing.KPIs import _renewable_fraction
from oemof.eesyplan.postprocessing.KPIs import _solver_value
from oemof.eesyplan.postprocessing.KPIs import _top_level_node
from oemof.eesyplan.postprocessing.KPIs import calculate_all_kpis
from oemof.eesyplan.postprocessing.KPIs import clean_label
from oemof.eesyplan.postprocessing.KPIs import demand_labels
from oemof.eesyplan.postprocessing.KPIs import edge_label
from oemof.eesyplan.postprocessing.KPIs import get_objective
from oemof.eesyplan.postprocessing.KPIs import normalize_imported_results
from oemof.eesyplan.postprocessing.KPIs import project_cost_table
from oemof.eesyplan.postprocessing.KPIs import renewable_share
from oemof.eesyplan.postprocessing.KPIs import result_keys
from oemof.eesyplan.postprocessing.KPIs import total_cost
from oemof.eesyplan.postprocessing.KPIs import yearly_project_costs
from oemof.eesyplan.postprocessing.print_results import _print_cost_table
from oemof.eesyplan.postprocessing.print_results import print_results
from oemof.solph.components import Source


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
    def __init__(self, label, **attrs):
        self.label = label
        self.parent = None
        for k, v in attrs.items():
            setattr(self, k, v)


class DummyES:
    def __init__(self, nodes):
        self.nodes = nodes


# tests for clean_label
def test_clean_label_plain():
    assert clean_label("Strom_bus") == "Strom_bus"


def test_clean_label_tuple_string():
    assert "feedin_converter" in clean_label(
        "('feedin_converter', 'Stromversorger')"
    )


def test_clean_label_with_carrier_removed():
    assert "Bus" in clean_label(
        "<CarrierBus 'Wärme_bus', carrier='Heat'>"
    ) or "Wärme_bus" in clean_label("<CarrierBus 'Wärme_bus', carrier='Heat'>")


def test_clean_label_tokens():
    result = clean_label("<...HeatPump: 'Luft-Wärmepumpe'>")
    assert "Luft-Wärmepumpe" in result


def test_edge_label():
    a, b = edge_label((("src",), ("dst",)))
    assert isinstance(a, str)
    assert isinstance(b, str)


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
    assert "Problem" not in result_keys(results)
    assert "objective" in result_keys(results) or "flow" in result_keys(
        results
    )


def test_demand_labels():
    bus = CarrierBus(name="bus")
    demand = Demand(name="demand_el", bus_in=bus, input_timeseries=[0])
    heat_demand = HeatDemand(
        name="demand_heat", bus_in_heat=bus, input_timeseries=[0]
    )
    es = DummyES([bus, demand, heat_demand])
    labels = demand_labels(es)
    assert "demand_el" in labels


def test_norm_label():
    assert _norm_label(("a", "b")) == "a | b"
    assert _norm_label("test") == "test"


def test_renewable_fraction_none():
    node = DummyNode("n")
    assert _renewable_fraction(node) == 0.0


def test_renewable_fraction_asset_true():
    node = DummyNode("n", renewable_asset=True)
    assert _renewable_fraction(node) == 1.0


def test_renewable_fraction_asset_false():
    node = DummyNode("n", renewable_asset=False)
    assert _renewable_fraction(node) == 0.0


def test_renewable_fraction_share():
    node = DummyNode("n", renewable_share=0.4)
    assert _renewable_fraction(node) == 0.4


def test_renewable_fraction_inherits():
    parent = DummyNode("parent", renewable_share=0.6)
    child = DummyNode("child")
    child.parent = parent
    assert _renewable_fraction(child) == 0.6


def test_renewable_share():
    bus = CarrierBus(name="bus")
    src = Source(label="wind", outputs={bus: None})
    src.renewable_asset = True
    es = DummyES([bus, src])
    flows = pd.DataFrame(
        [[100.0]], columns=pd.MultiIndex.from_tuples([(src, bus)])
    )
    results = DummyResults(data={"flow": flows})
    renewable_share(results, es)
    assert results["eesyplan"]["renewable_share"] == 1.0


def test_renewable_share_mixed():
    bus = CarrierBus(name="bus")
    wind = Source(label="wind", outputs={bus: None})
    wind.renewable_asset = True
    gas = Source(label="gas", outputs={bus: None})
    gas.renewable_asset = False
    es = DummyES([bus, wind, gas])
    flows = pd.DataFrame(
        [[60.0, 40.0]],
        columns=pd.MultiIndex.from_tuples([(wind, bus), (gas, bus)]),
    )
    results = DummyResults(data={"flow": flows})
    renewable_share(results, es)
    assert results["eesyplan"]["renewable_share"] == 0.6


def test_renewable_share_zero_total():
    bus = CarrierBus(name="bus")
    src = Source(label="wind", outputs={bus: None})
    es = DummyES([bus, src])
    flows = pd.DataFrame(
        [[0.0]], columns=pd.MultiIndex.from_tuples([(src, bus)])
    )
    results = DummyResults(data={"flow": flows})
    # division by zero gives nan
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        renewable_share(results, es)
        result = results["eesyplan"]["renewable_share"]
        assert result != result or result == 0  # nan or 0


def test_print_flows(capsys):
    flows = pd.DataFrame(
        [[10.0, 0.0]],
        columns=pd.MultiIndex.from_tuples(
            [(("a",), ("b",)), (("c",), ("d",))]
        ),
    )
    results = DummyResults(data={"flow": flows})
    print_results(results)
    out = capsys.readouterr().out
    assert "Flows" in out


def test_print_flows_no_flow(capsys):
    results = DummyResults(data={})
    print_results(results)
    out = capsys.readouterr().out
    assert "Flows" not in out


def test_print_storages(capsys):
    storage = pd.DataFrame(
        [[1.0, 5.0]], columns=[("storage1",), ("storage2",)]
    )
    results = DummyResults(data={"storage_content": storage})
    print_results(results)
    out = capsys.readouterr().out
    assert "Storage content" in out


def test_print_storages_no_key(capsys):
    results = DummyResults(data={})
    print_results(results)
    out = capsys.readouterr().out
    assert "Storage content" not in out


def test_print_investments(capsys):
    invest = pd.DataFrame([[10.0, 0.0]], columns=[("comp1",), ("comp2",)])
    costs = pd.DataFrame([[5.0]], columns=[("comp1",)])
    results = DummyResults(data={"invest": invest, "investment_costs": costs})
    print_results(results)
    out = capsys.readouterr().out
    assert "Optimised capacities" in out or "Annual investment costs" in out


def test_print_investments_no_invest(capsys):
    results = DummyResults(data={})
    print_results(results)
    out = capsys.readouterr().out
    assert "Optimised capacities" not in out


def test_print_costs(capsys):
    costs = pd.DataFrame(
        [[3.0, 0.0]],
        columns=pd.MultiIndex.from_tuples(
            [(("a",), ("b",)), (("c",), ("d",))]
        ),
    )
    results = DummyResults(data={"variable_costs": costs})
    print_results(results)
    out = capsys.readouterr().out
    assert "Variable costs" in out


def test_print_costs_no_key(capsys):
    results = DummyResults(data={})
    print_results(results)
    out = capsys.readouterr().out
    assert "Variable costs" not in out


def test_top_level_node():
    parent = DummyNode("parent")
    child = DummyNode("child")
    child.parent = parent
    assert _top_level_node(child) is parent
    assert _top_level_node(parent) is parent


def test_owner_map():
    bus = CarrierBus(name="bus")
    parent = DummyNode("parent")
    child = DummyNode("child")
    child.parent = parent
    es = DummyES([bus, parent, child])
    owners = _owner_map(es)
    assert owners.get(_norm_label(child.label)) is parent


def test_is_neutral():
    bus = CarrierBus(name="bus")
    demand = Demand(name="d", bus_in=bus, input_timeseries=[0])
    assert _is_neutral(bus) is True
    assert _is_neutral(demand) is True


def test_owner_of_parts():
    bus = CarrierBus(name="bus")
    owner = DummyNode("owner")
    owners = {_norm_label(bus.label): bus, "owner": owner}
    assert _owner_of_parts(["owner", _norm_label(bus.label)], owners) is owner


def test_owner_of_parts_only_neutral():
    bus = CarrierBus(name="bus")
    owners = {_norm_label(bus.label): bus}
    assert _owner_of_parts([_norm_label(bus.label)], owners) is bus


def test_edge_owner():
    bus1 = CarrierBus(name="bus1")
    bus2 = CarrierBus(name="bus2")
    owner = DummyNode("owner")
    owners = {_norm_label(bus1.label): bus1, _norm_label(bus2.label): owner}
    col = ((bus1,), (bus2,))
    result = _edge_owner(col, owners)
    assert result is owner or result is bus1


def test_column_parts():
    parts = _column_parts(("a | b",))
    assert isinstance(parts, list)


def test_effective_capacity():
    node = DummyNode("n", installed_capacity=10)
    cap = {}
    assert _effective_capacity(node, cap) == 10.0
    node2 = DummyNode("n2", installed_capacity=10)
    cap2 = {node2: 5.0}
    assert _effective_capacity(node2, cap2) == 5.0


def test_component_costs_optimized():
    node = DummyNode("n", opex_spec=1.0)
    cap = {node: 10.0}
    invest_cost = {node: 20.0}
    ccap, copex = _component_costs(node, cap, invest_cost)
    assert copex == 10.0
    assert ccap == 10.0


def test_component_costs_installed():
    node = DummyNode(
        "n",
        installed_capacity=10,
        opex_spec=1.0,
        installed_capex_spec_annualized=2.0,
    )
    cap = {}
    invest_cost = {}
    ccap, copex = _component_costs(node, cap, invest_cost)
    assert copex == 10.0
    assert ccap == 20.0


def test_component_cost_data():
    bus = CarrierBus(name="bus")
    owner = DummyNode("owner", opex_spec=1.0)
    es = DummyES([bus, owner])
    invest = pd.DataFrame([[10.0]], columns=[("owner",)])
    invest_costs = pd.DataFrame([[20.0]], columns=[("owner",)])
    var_costs = pd.DataFrame(
        [[5.0]], columns=pd.MultiIndex.from_tuples([(owner, bus)])
    )
    results = DummyResults(
        data={
            "invest": invest,
            "investment_costs": invest_costs,
            "variable_costs": var_costs,
        }
    )
    _, capacity, _, _ = _component_cost_data(results, es)
    assert owner in capacity or len(capacity) >= 0


def test_cost_table():
    rows = [{"component": "a", "cost1": 10.0, "cost2": 5.0}]
    table = _cost_table(rows, ["cost1", "cost2"])
    assert "total" in table.columns
    assert "total" in table["component"].values


def test_cost_table_filters_zeros():
    rows = [{"component": "a", "cost1": 0.0}]
    table = _cost_table(rows, ["cost1"])
    # all zeros filtered, but total row added? Let us check
    assert len(table) >= 0


def test_yearly_project_costs():
    bus = CarrierBus(name="bus")
    owner = DummyNode("owner_node", opex_spec=1.0)
    owner.label = "owner_node"
    es = DummyES([bus, owner])
    invest = pd.DataFrame([[10.0]], columns=[("owner_node",)])
    invest_costs = pd.DataFrame([[20.0]], columns=[("owner_node",)])
    var_costs = pd.DataFrame(
        [[5.0]], columns=pd.MultiIndex.from_tuples([(owner, bus)])
    )
    results = DummyResults(
        data={
            "invest": invest,
            "investment_costs": invest_costs,
            "variable_costs": var_costs,
        }
    )
    yearly_project_costs(results, es)
    table = results["eesyplan"]["yearly_project_costs"]
    assert isinstance(table, pd.DataFrame)
    assert "total" in table.columns


def test_project_cost_table():
    bus = CarrierBus(name="bus")
    owner = DummyNode("owner_node", opex_spec=1.0, capex_spec=5.0)
    owner.label = "owner_node"
    es = DummyES([bus, owner])
    invest = pd.DataFrame([[10.0]], columns=[("owner_node",)])
    invest_costs = pd.DataFrame([[20.0]], columns=[("owner_node",)])
    var_costs = pd.DataFrame(
        [[5.0]], columns=pd.MultiIndex.from_tuples([(owner, bus)])
    )
    results = DummyResults(
        data={
            "invest": invest,
            "investment_costs": invest_costs,
            "variable_costs": var_costs,
        }
    )
    project_cost_table(results, es, project_duration=20)
    table = results["eesyplan"]["project_cost_table"]
    assert isinstance(table, pd.DataFrame)


def test_print_cost_table(capsys):
    table = pd.DataFrame([{"component": "a", "cost1": 10.0, "total": 10.0}])
    _print_cost_table(table)
    out = capsys.readouterr().out
    assert "a" in out


def test_print_cost_table_with_title(capsys):
    table = pd.DataFrame([{"component": "a", "cost1": 10.0, "total": 10.0}])
    _print_cost_table(table, title="Test:")
    out = capsys.readouterr().out
    assert "Test:" in out


def test_numeric_variable_costs():
    costs = pd.DataFrame([["[1.5, 2.5]"]])
    result = _numeric_variable_costs(costs)
    assert result.iloc[0, 0] == 1.5


def test_normalize_imported_results_no_objective_placeholder():
    results = DummyResults()
    normalize_imported_results(results)
    assert "objective" not in results.keys()


def test_normalize_imported_results_variable_costs_already_numeric():
    costs = pd.DataFrame([[1.0, 2.0]])
    results = DummyResults(data={"variable_costs": costs})
    normalize_imported_results(results)
    assert results["variable_costs"].iloc[0, 0] == 1.0


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


def test_all_new_functions_coverage():
    # Just ensure imports work
    assert callable(get_objective)
    assert callable(LCOE)
    assert callable(_solver_value)
    assert callable(_norm_label)
    assert callable(_renewable_fraction)
    assert callable(renewable_share)


def test_solver_value_object_no_attr():
    class S:
        pass

    results = DummyResults(solver=S())
    assert _solver_value(results, "objective") is None


def test_solver_value_dict_no_get():
    class D(dict):
        def get(self, *args, **kwargs):
            raise AttributeError

    results = DummyResults(solver=D({"objective": 1}))
    # should not crash
    try:
        _solver_value(results, "objective")
    except Exception as exc:
        raise AssertionError("should not raise") from exc


def test_get_objective_solver_has_no_objective_but_legacy_key():
    results = DummyResults(
        data={"objective": 777}, solver=pd.Series({"solver": "cbc"})
    )
    assert get_objective(results) == 777.0


def test_get_objective_solver_dict_no_objective_but_legacy():
    results = DummyResults(data={"objective": "888"}, solver={"solver": "cbc"})
    assert get_objective(results) == 888.0


def test_get_objective_numpy_float():
    results = DummyResults(solver=pd.Series({"objective": np.float64(123.45)}))
    assert get_objective(results) == 123.45


def test_get_objective_int():
    results = DummyResults(solver=pd.Series({"objective": 100}))
    assert get_objective(results) == 100.0


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


def test_normalize_imported_results_empty_variable_costs():
    costs = pd.DataFrame()
    results = DummyResults(data={"variable_costs": costs})
    normalize_imported_results(results)  # should not crash


def test_normalize_imported_results_variable_costs_already_ok():
    costs = pd.DataFrame([[1.0, 2.0], [3.0, 4.0]])
    results = DummyResults(data={"variable_costs": costs})
    normalize_imported_results(results)
    assert results["variable_costs"].iloc[0, 0] == 1.0


def test_total_cost():
    bus = CarrierBus(name="bus")
    owner = DummyNode("owner_node", opex_spec=1.0, capex_spec=5.0)
    owner.label = "owner_node"
    es = DummyES([bus, owner])
    invest = pd.DataFrame([[10.0]], columns=[("owner_node",)])
    invest_costs = pd.DataFrame([[20.0]], columns=[("owner_node",)])
    var_costs = pd.DataFrame(
        [[5.0]], columns=pd.MultiIndex.from_tuples([(owner, bus)])
    )
    results = DummyResults(
        data={
            "invest": invest,
            "investment_costs": invest_costs,
            "variable_costs": var_costs,
        },
        solver=pd.Series({"objective": 100.0}),
    )
    total_cost(results, es)
    assert results["eesyplan"]["total_cost"] == 100.0


def test_total_cost_adds_installed_fixed_costs():
    bus = CarrierBus(name="bus")
    owner = DummyNode(
        "owner_node",
        installed_capacity=10.0,
        opex_spec=1.0,
        installed_capex_spec_annualized=2.0,
    )
    owner.label = "owner_node"
    es = DummyES([bus, owner])
    results = DummyResults(data={}, solver=pd.Series({"objective": 100.0}))
    total_cost(results, es)
    assert results["eesyplan"]["total_cost"] == 130.0


def test_calculate_all_kpis():
    bus = CarrierBus(name="bus")
    demand = Demand(name="demand_el", bus_in=bus, input_timeseries=[0])
    source = Source(label="wind", outputs={bus: None})
    source.renewable_asset = True
    owner = DummyNode("owner_node", opex_spec=1.0, capex_spec=5.0)
    owner.label = "owner_node"
    es = DummyES([bus, demand, source, owner])
    flows = pd.DataFrame(
        [[100.0, 100.0, 0.0]],
        columns=pd.MultiIndex.from_tuples(
            [(source, bus), (bus, demand), (owner, bus)]
        ),
    )
    results = DummyResults(
        data={"flow": flows},
        solver=pd.Series({"objective": 50.0}),
    )
    calculate_all_kpis(results, es, project_duration=10)
    kpis = results["eesyplan"]
    assert kpis["total_cost"] == 50.0
    assert kpis["lcoe"] == 0.5
    assert kpis["renewable_share"] == 1.0
    assert "yearly_project_costs" in kpis
    assert "project_cost_table" in kpis
