import warnings
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from oemof.datapackage import datapackage  # noqa
from oemof.eesyplan import CarrierBus
from oemof.eesyplan import Demand
from oemof.eesyplan import DsoElectricity
from oemof.eesyplan import ElectricalStorage
from oemof.eesyplan import EnergySystem
from oemof.eesyplan import Project
from oemof.eesyplan import PvPlant
from oemof.eesyplan import WindTurbine
from oemof.eesyplan import optimise
from oemof.eesyplan.datapackage import energy_system as es
from oemof.eesyplan.postprocessing.graphs import capacities
from oemof.eesyplan.postprocessing.graphs import capacities_graph
from oemof.eesyplan.postprocessing.graphs import plot_annual_costs
from oemof.eesyplan.postprocessing.graphs import plot_renewable_vs_nonrenewable
from oemof.eesyplan.postprocessing.graphs import sankey
from oemof.eesyplan.postprocessing.graphs import sankey_2
from oemof.solph.components import Source
from oemof.tools.debugging import ExperimentalFeatureWarning

DATA_PATH = Path("../test_data", "simple_script_data")

DATA_FILES = {
    "pv": Path("pv_profile.csv"),
    "demand_heat": Path("heat_demand.csv"),
    "wind": Path("wind_profile.csv"),
    "demand_elec": Path("electricity_demand.csv"),
}


def simple_script(pv_installed_cap=1.0, optimize_battery=False):
    # Read data file
    data = {}
    for key, fn in DATA_FILES.items():
        path = Path(Path(__file__).parent, DATA_PATH, fn)
        data[key] = pd.read_csv(path, header=None).squeeze()

    project = Project(
        name="test", economic_period=20, tax=0, discount_factor=0
    )

    # ####################### initialize the energy system ####################
    energy_system = EnergySystem(2023, number=10)

    # ######################### create energysystem components ################

    # carrier
    bus_elec = CarrierBus(name="electricity")

    energy_system.add(bus_elec)

    energy_system.add(
        DsoElectricity(
            name="My_DSO",
            bus_electricity=bus_elec,
            energy_price=5,
            feedin_tariff=0.04,
        )
    )

    # sources
    energy_system.add(
        WindTurbine(
            name="wind",
            bus_out_electricity=bus_elec,
            input_timeseries=data["wind"],
            maximum_capacity=25,
            project_data=project,
        )
    )

    energy_system.add(
        PvPlant(
            name="pv",
            bus_out_electricity=bus_elec,
            project_data=project,
            capex_spec=0.01,
            maximum_capacity=10 * pv_installed_cap,
            input_timeseries=data["pv"],
        )
    )

    energy_system.add(
        ElectricalStorage(
            name="Batterie",
            bus_in_electricity=bus_elec,
            age_installed=0,
            installed_capacity=1000,
            maximum_capacity=None,
            capex_spec=3.0,
            opex_spec=5.0,
            variable_costs=0.0,
            lifetime=10,
            soc_max=1,
            soc_min=0,
            c_rate_charge=1.0,
            efficiency_charge=0.99,
            project_data=project,
            loss_rate=0.000,
        )
    )

    # demands (electricity/heat)
    energy_system.add(
        Demand(
            name="demand_el",
            bus_in=bus_elec,
            input_timeseries=data["demand_elec"],
        )
    )
    return optimise(energy_system), energy_system


def test_graph_capacities():
    res, esys = simple_script()

    capacities_graph(res["invest"], esys)


class _Component:
    """Hashable stand-in for an energy system component."""

    def __init__(self, label, **attributes):
        self.label = label
        self.parent = None
        for name, value in attributes.items():
            setattr(self, name, value)


def test_capacities_shows_installed_or_optimized_components_with_costs():
    bus = CarrierBus(name="electricity")
    wind = _Component(
        "wind", capex_spec=1100, opex_spec=10, installed_capacity=None
    )
    pv = _Component("pv", capex_spec=600, opex_spec=0, installed_capacity=2)
    battery = _Component("battery", capex_spec=0, opex_spec=5)
    legacy = _Component(
        "legacy", capex_spec=0, opex_spec=0, installed_capacity=5
    )
    idle = _Component("idle", capex_spec=600, opex_spec=0)
    noise = _Component("noise", capex_spec=600, opex_spec=0)
    free = _Component("free", capex_spec=0, opex_spec=0)
    commodity = _Component("rgas")
    es_stub = SimpleNamespace(
        nodes=[bus, wind, pv, battery, legacy, idle, noise, free, commodity]
    )
    imported = {
        "invest": pd.DataFrame(
            [{"wind": 390.0, "battery": 8000.0, "noise": 1e-10, "free": 5.0}]
        ),
    }

    fig = capacities(imported, es_stub)

    assert len(fig.data) == 2
    assert fig.data[0].name == "Installed"
    assert fig.data[1].name == "Optimized"
    assert list(fig.data[0].x) == ["wind", "pv", "battery", "legacy"]
    assert list(fig.data[0].y) == [None, 2.0, None, 5.0]
    assert list(fig.data[1].y) == [390.0, None, 8000.0, None]
    assert list(fig.data[0].customdata) == [None, "2.0", None, "5.0"]
    assert list(fig.data[1].customdata) == ["390.0", None, "8 000.0", None]


def test_capacities_without_investments():
    pv = _Component("pv", capex_spec=600, opex_spec=0, installed_capacity=2)
    idle = _Component("idle", capex_spec=600, opex_spec=0)
    es_stub = SimpleNamespace(nodes=[pv, idle])

    fig = capacities({"invest": pd.DataFrame()}, es_stub)

    assert len(fig.data) == 2
    assert list(fig.data[0].x) == ["pv"]
    assert list(fig.data[0].y) == [2.0]
    assert list(fig.data[1].y) == [None]


def test_storage_exposes_cost_and_installed_capacity():
    _, esys = simple_script()
    battery = next(node for node in esys.nodes if node.label == "Batterie")

    assert battery.capex_spec == 3.0
    assert battery.opex_spec == 5.0
    assert battery.installed_capacity == 1000


def test_capacities_shows_installed_storage():
    res, esys = simple_script()

    fig = capacities({"invest": res["invest"]}, esys)

    installed = dict(zip(fig.data[0].x, fig.data[0].y, strict=True))
    assert installed["Batterie"] == 1000


warnings.filterwarnings("ignore", category=ExperimentalFeatureWarning)


def test_sankey_diagram():
    path = Path(Path(__file__).parent, "../test_data", "openPlan_package")
    energy_system = es.create_energy_system_from_dp(path)
    results = optimise(energy_system)

    fig, _ = sankey(results["flow"], es=energy_system)
    actual_dict = fig.to_dict()

    actual_data = actual_dict["data"][0]

    # Überprüfe Struktur
    assert actual_data["type"] == "sankey"

    # Überprüfe konkrete erwartete Werte
    assert len(actual_data["node"]["label"]) == 11  # Z.B. 11 Nodes erwartet
    assert len(actual_data["link"]["source"]) == 12  # Z.B. 12 Links erwartet

    # Überprüfe, dass alle Fließwerte positiv sind
    assert all(v >= 0 for v in actual_data["link"]["value"])

    # Überprüfe Gesamtfluss mit Toleranz
    total_flow = sum(actual_data["link"]["value"])
    expected_total_flow = 888.0125834243663
    assert abs(total_flow - expected_total_flow) < 1e-6


def test_sankey_2_keeps_excess_as_separate_node():
    class Node:
        def __init__(self, label):
            self.label = label

    bus = Node("BUS")
    excess = Node(("excess", "BUS"))
    source = Node("source")

    flows = pd.DataFrame(
        [[1.0, 2.0]],
        columns=pd.MultiIndex.from_tuples([(source, bus), (bus, excess)]),
    )

    _, links = sankey_2(flows)

    edges = set(zip(links["source"], links["target"], strict=True))
    assert ("BUS", "BUS (excess)") in edges
    assert not (links["source"] == links["target"]).any()


def test_plot_annual_costs(monkeypatch):
    table = pd.DataFrame(
        {
            "component": ["component_a", "component_b", "total"],
            "annualized investment cost": [10.0, -5.0, 5.0],
            "fix operational costs": [2.0, 1.0, 3.0],
            "dispatch costs": [3.0, -2.0, 1.0],
            "total": [15.0, -6.0, 9.0],
        }
    )

    def fake_yearly_project_costs(results, es):
        results["eesyplan"] = {"yearly_project_costs": table}

    monkeypatch.setattr(
        "oemof.eesyplan.postprocessing.graphs.yearly_project_costs",
        fake_yearly_project_costs,
    )

    fig = plot_annual_costs({}, None)

    assert fig.layout.barmode == "relative"
    assert [trace.name for trace in fig.data] == [
        "annualized investment cost",
        "fix operational costs",
        "dispatch costs",
    ]
    for trace in fig.data:
        assert list(trace.x) == ["component_a", "component_b"]


def test_plot_renewable_vs_nonrenewable():
    grid = Source(label="grid", outputs={})
    grid.renewable_share = 0.4
    wind = Source(label="wind", outputs={})
    wind.renewable_asset = True
    gas = Source(label="gas", outputs={})
    gas.renewable_asset = False
    bus = CarrierBus(name="bus")

    flows = pd.DataFrame(
        [[100.0, 50.0, 25.0]],
        columns=pd.MultiIndex.from_tuples(
            [(grid, bus), (wind, bus), (gas, bus)]
        ),
    )
    es_stub = SimpleNamespace(nodes=[grid, wind, gas])

    fig = plot_renewable_vs_nonrenewable(
        flows, es_stub, threshold=0, unit="Wh"
    )

    assert fig.layout.barmode == "stack"
    segments = {(trace.x[0], trace.name): trace.y[0] for trace in fig.data}
    assert segments == {
        ("Renewable", "grid"): 40.0,
        ("Renewable", "wind"): 50.0,
        ("Non-renewable", "grid"): 60.0,
        ("Non-renewable", "gas"): 25.0,
    }
    grid_colors = {
        trace.marker.color for trace in fig.data if trace.name == "grid"
    }
    assert len(grid_colors) == 1

    annotations = [annotation.text for annotation in fig.layout.annotations]
    assert "Total<br>90.0 Wh" in annotations
    assert "Total<br>85.0 Wh" in annotations
