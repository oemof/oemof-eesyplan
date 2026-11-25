"""Tests for oemof.eesyplan.postprocessing.graphs."""

import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from oemof.eesyplan import CarrierBus
from oemof.eesyplan import Demand
from oemof.eesyplan import DsoElectricity
from oemof.eesyplan import ElectricalStorage
from oemof.eesyplan import EnergySystem
from oemof.eesyplan import Project
from oemof.eesyplan import PvPlant
from oemof.eesyplan import WindTurbine
from oemof.eesyplan import optimise
from oemof.eesyplan.datapackage import energy_system as dp_energy_system
from oemof.eesyplan.postprocessing import graphs
from oemof.solph.components import Source

pytestmark = pytest.mark.filterwarnings(
    "ignore::oemof.tools.debugging.ExperimentalFeatureWarning"
)

# The test data live in tests/test_data (one level above this directory).
TEST_DATA = Path(__file__).resolve().parent.parent / "test_data"
SIMPLE_SCRIPT_DATA = TEST_DATA / "simple_script_data"
DATA_FILES = {
    "pv": "pv_profile.csv",
    "wind": "wind_profile.csv",
    "demand_elec": "electricity_demand.csv",
}


# ---------------------------------------------------------------------------
# Stand-ins and small helpers
# ---------------------------------------------------------------------------


class _N:
    """Hashable node stand-in whose str() is its label."""

    def __init__(self, label, parent=None, **attrs):
        self.label = label
        self.parent = parent
        for key, value in attrs.items():
            setattr(self, key, value)

    def __str__(self):
        return str(self.label)


def _stub_class(name):
    """Create a stub class carrying the given ``__name__``.

    The graphs group components by ``type(node).__name__``.
    """
    return type(name, (_N,), {})


# The stubs must not shadow the real WindTurbine / PvPlant imported above.
FakeWindTurbine = _stub_class("WindTurbine")
FakePvPlant = _stub_class("PvPlant")


class _Results(dict):
    """Minimal results object with an attached energy system."""

    def __init__(self, data, es):
        super().__init__(data)
        self.energy_system = es


def _source(label, **attrs):
    node = Source(label=label, outputs={})
    for key, value in attrs.items():
        setattr(node, key, value)
    return node


def _flows(columns, values, index=None):
    return pd.DataFrame(
        np.array(values, dtype=float),
        index=index,
        columns=pd.MultiIndex.from_tuples(columns),
    )


def _single_link_flows(periods, value):
    """Flow table with one link and a constant value."""
    return pd.DataFrame(
        np.ones((periods, 1)) * value,
        index=pd.date_range("2023-01-01", periods=periods, freq="h"),
        columns=pd.MultiIndex.from_tuples(
            [("source1", "bus1")], names=["source", "target"]
        ),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _load_profiles():
    return {
        key: pd.read_csv(SIMPLE_SCRIPT_DATA / name, header=None).squeeze()
        for key, name in DATA_FILES.items()
    }


def _build_energy_system(number, wind_max, pv_max, pv_capex_spec=None):
    data = _load_profiles()
    project = Project(
        name="test", economic_period=20, tax=0, discount_factor=0
    )
    esys = EnergySystem(2023, number=number)

    bus_elec = CarrierBus(name="electricity")
    esys.add(bus_elec)
    esys.add(
        DsoElectricity(
            name="My_DSO",
            bus_electricity=bus_elec,
            energy_price=5,
            feedin_tariff=0.04,
        )
    )
    esys.add(
        WindTurbine(
            name="wind",
            bus_out_electricity=bus_elec,
            input_timeseries=data["wind"],
            maximum_capacity=wind_max,
            project_data=project,
        )
    )
    pv_kwargs = {} if pv_capex_spec is None else {"capex_spec": pv_capex_spec}
    esys.add(
        PvPlant(
            name="pv",
            bus_out_electricity=bus_elec,
            project_data=project,
            maximum_capacity=pv_max,
            input_timeseries=data["pv"],
            **pv_kwargs,
        )
    )
    esys.add(
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
            loss_rate=0.0,
        )
    )
    esys.add(
        Demand(
            name="demand_el",
            bus_in=bus_elec,
            input_timeseries=data["demand_elec"],
        )
    )
    return esys


# Module scope: the (expensive) optimisation runs only once per file.
# Tests must treat these objects as read-only.
@pytest.fixture(scope="module")
def sample_energy_system():
    return _build_energy_system(number=24, wind_max=250, pv_max=250)


@pytest.fixture(scope="module")
def sample_results(sample_energy_system):
    return optimise(sample_energy_system)


@pytest.fixture(scope="module")
def sample_flows_df(sample_results):
    return sample_results["flow"]


@pytest.fixture(scope="module")
def simple_script_result():
    esys = _build_energy_system(
        number=10, wind_max=25, pv_max=10, pv_capex_spec=0.01
    )
    return optimise(esys), esys


@pytest.fixture
def empty_flows_df():
    """Empty DataFrame with the correct MultiIndex structure."""
    columns = pd.MultiIndex.from_tuples(
        [("source1", "bus1")], names=["source", "target"]
    )
    return pd.DataFrame(columns=columns)


@pytest.fixture
def flows_with_zeros():
    """DataFrame in which one of the links carries no energy."""
    dates = pd.date_range("2023-01-01", periods=10, freq="h")
    columns = pd.MultiIndex.from_tuples(
        [("source1", "bus1"), ("source2", "bus2"), ("source3", "bus3")],
        names=["source", "target"],
    )
    data = np.array([[10, 0, 5]] * 10)
    return pd.DataFrame(data, index=dates, columns=columns)


@pytest.fixture
def complex_flows_df():
    """Larger DataFrame with many time steps and several components."""
    dates = pd.date_range("2023-01-01", periods=100, freq="h")
    columns = pd.MultiIndex.from_tuples(
        [
            ("solar", "grid"),
            ("wind", "grid"),
            ("grid", "load1"),
            ("grid", "load2"),
            ("grid", "battery"),
            ("battery", "grid"),
        ],
        names=["source", "target"],
    )
    # A fixed seed keeps the test reproducible.
    rng = np.random.default_rng(0)
    data = rng.random((100, 6)) * 50 + np.sin(np.arange(100)[:, None]) * 25
    return pd.DataFrame(np.abs(data), index=dates, columns=columns)


# ---------------------------------------------------------------------------
# Small helpers of the module
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "decimals", "expected"),
    [
        (None, 1, ""),
        (float("nan"), 1, ""),
        (1234.56, 1, "1 234.6"),
        (1234.56, 0, "1 235"),
        ("abc", 1, "abc"),
    ],
)
def test_format_number(value, decimals, expected):
    assert graphs._format_number(value, decimals) == expected


def test_label_of():
    assert graphs._label_of(_N("wind")) == "wind"
    assert graphs._label_of("<x.HeatPump: 'Pump'>") == "Pump"
    assert graphs._label_of("<CarrierBus 'bus', carrier='Heat'>") == "bus"
    assert graphs._label_of("plain") == "plain"


def test_rgba():
    assert graphs._rgba("#ff0000", 0.3) == "rgba(255, 0, 0, 0.3)"


def test_facade_label_and_facade_of():
    assert graphs._facade_label(_N(("converter", "Gas"))) == "Gas"
    assert graphs._facade_label(_N(("excess", "BUS"))) == "BUS (excess)"
    assert graphs._facade_label(_N("plain")) == "plain"
    assert graphs._facade_label(_N("excess | BUS")) == "BUS (excess)"
    assert graphs._facade_label(_N("internal | Gas")) == "Gas"
    assert graphs._facade_label("text") == "text"
    assert graphs._facade_of(_N(("internal_bus", "Gas"))) == "Gas"
    assert graphs._facade_of(_N(("absolute_losses", "Net"))) == (
        "Net (absolute_losses)"
    )


def test_component_type_index_and_group_key():
    assert graphs._component_type_index("wind_turbine") == 5
    assert graphs._component_type_index("bus") == 0
    assert graphs._component_type_index("unknown") is None
    assert graphs._type_group_key(("s", "wind_turbine", "W")) == (
        False,
        5,
        "W",
    )
    assert graphs._type_group_key(("s", "unknown", "X")) == (True, 0, "X")


def test_node_type_color():
    type_map = {"wind": "wind_turbine"}

    assert graphs._node_type_color(_N("wind"), type_map) == "#2ca02c"
    assert graphs._node_type_color(_N("other"), type_map) is None
    # Internal nodes are looked up by their facade (last label element).
    internal = _N(("converter", "wind"), parent=object())
    assert graphs._node_type_color(internal, type_map) == "#2ca02c"


# ---------------------------------------------------------------------------
# sankey (stubs)
# ---------------------------------------------------------------------------


def test_sankey_node_colors_by_role():
    bus = CarrierBus(name="bus")
    bus_name = str(bus.label)
    es = SimpleNamespace(
        nodes=[
            bus,
            _N("src", inputs={}, outputs={"o": 1}),
            _N("mid", inputs={"i": 1}, outputs={"o": 1}),
            _N("snk", inputs={"i": 1}, outputs={}),
        ]
    )
    flows = _flows(
        [("src", "mid"), ("mid", "snk"), (bus_name, "mid")],
        [[1.0, 1.0, 1.0]],
    )

    fig, _ = graphs.sankey(flows, es=es)

    colors = dict(
        zip(fig.data[0].node.label, fig.data[0].node.color, strict=True)
    )
    assert colors == {
        "src": "blue",
        "mid": "green",
        "snk": "red",
        bus_name: "grey",
    }


# ---------------------------------------------------------------------------
# sankey_2
# ---------------------------------------------------------------------------


def _sankey_2_system():
    bus = CarrierBus(name="bus")
    src = _N("src", inputs={}, outputs={"o": 1})
    conv = _N("conv", inputs={"i": 1}, outputs={"o": 1})
    snk = _N("snk", inputs={"i": 1}, outputs={})
    wind = _N("wind", inputs={}, outputs={"o": 1})
    ghost = _N("ghost")
    es = SimpleNamespace(nodes=[bus, src, conv, snk, wind])
    flows = _flows(
        [(src, bus), (bus, conv), (conv, snk), (wind, bus), (ghost, bus)],
        [[1.0] * 5, [2.0] * 5],
        index=pd.date_range("2023-01-01", periods=2, freq="h"),
    )
    return bus, es, flows


def test_sankey_2_results_object_and_node_colors():
    bus, es, flows = _sankey_2_system()
    results = _Results(
        {
            "flow": flows,
            "component_type_mapping": {"wind": "wind_turbine"},
        },
        es,
    )

    fig, links = graphs.sankey_2(results)

    colors = dict(
        zip(fig.data[0].node.label, fig.data[0].node.color, strict=True)
    )
    assert colors == {
        "src": "blue",
        "conv": "green",
        "snk": "red",
        "wind": "#2ca02c",
        str(bus.label): "grey",
        "ghost": "#17becf",
    }
    assert fig.data[0].node.align == "left"
    assert len(links) == 5


def test_sankey_2_row_selection_adds_timestamp():
    _, es, flows = _sankey_2_system()

    fig_int, links_int = graphs.sankey_2(flows, es=es, row=1)
    fig_label, links_label = graphs.sankey_2(flows, es=es, row=flows.index[0])

    assert "Timestamp" in fig_int.data[0].link.hovertemplate
    assert links_int["timestamp"].iloc[0] == str(flows.index[1])
    assert links_label["timestamp"].iloc[0] == str(flows.index[0])
    # Row 1 is the second time step, row 0 the first one.
    assert list(links_int["value"]) == [2.0] * 5
    assert list(links_label["value"]) == [1.0] * 5


def test_sankey_2_without_aggregation_hover_and_agg_modes():
    _, _, flows = _sankey_2_system()

    fig, links = graphs.sankey_2(flows, agg="mean")
    _, links_max = graphs.sankey_2(flows, agg="max")

    assert "Timestamp" not in fig.data[0].link.hovertemplate
    assert list(links["value"]) == [1.5] * 5
    assert list(links_max["value"]) == [2.0] * 5


def test_sankey_2_without_collapsing_and_keeping_zero_links():
    src, dst = _N("src"), _N("dst")
    flows = _flows([(src, dst), (dst, src)], [[0.0, 3.0]])

    _, links = graphs.sankey_2(
        flows, drop_zero_links=False, collapse_fascades=False
    )

    assert list(links["source"]) == ["src", "dst"]
    assert 1e-9 in list(links["value"])


def test_sankey_2_validates_input():
    src, dst = _N("src"), _N("dst")
    flows = _flows([(src, dst)], [[1.0]])

    with pytest.raises(TypeError, match="MultiIndex"):
        graphs.sankey_2(pd.DataFrame({"a": [1.0]}))
    with pytest.raises(ValueError, match="exactly 2 column levels"):
        graphs.sankey_2(
            pd.DataFrame(
                [[1.0]], columns=pd.MultiIndex.from_tuples([("a", "b", "c")])
            )
        )
    with pytest.raises(ValueError, match="empty"):
        graphs.sankey_2(flows.iloc[0:0])
    with pytest.raises(ValueError, match="agg must be one of"):
        graphs.sankey_2(flows, agg="median")
    with pytest.raises(ValueError, match="No links remain"):
        graphs.sankey_2(_flows([(src, dst)], [[0.0]]))


class _PlainNode:
    """Node with nothing but a label (no ``parent`` attribute)."""

    def __init__(self, label):
        self.label = label


def test_sankey_2_keeps_excess_as_separate_node():
    bus = _PlainNode("BUS")
    excess = _PlainNode(("excess", "BUS"))
    source = _PlainNode("source")
    flows = pd.DataFrame(
        [[1.0, 2.0]],
        columns=pd.MultiIndex.from_tuples([(source, bus), (bus, excess)]),
    )

    _, links = graphs.sankey_2(flows)

    edges = set(zip(links["source"], links["target"], strict=True))
    assert ("BUS", "BUS (excess)") in edges
    assert not (links["source"] == links["target"]).any()


def test_sankey_2_keeps_absolute_losses_as_separate_node():
    network = _PlainNode("Heating Network")
    losses = _PlainNode(("absolute_losses", "Heating Network"))
    source = _PlainNode("source")
    flows = pd.DataFrame(
        [[1.0, 2.0]],
        columns=pd.MultiIndex.from_tuples(
            [(source, network), (network, losses)]
        ),
    )

    _, links = graphs.sankey_2(flows)

    edges = set(zip(links["source"], links["target"], strict=True))
    assert ("Heating Network", "Heating Network (absolute_losses)") in edges
    assert not (links["source"] == links["target"]).any()


# ---------------------------------------------------------------------------
# sankey (optimised energy system)
# ---------------------------------------------------------------------------


class TestSankey:
    """Tests for sankey()."""

    def test_basic_sum_aggregation(self, sample_flows_df):
        fig, links_df = graphs.sankey(sample_flows_df, title="Test Sankey")

        assert isinstance(fig, go.Figure)
        assert isinstance(links_df, pd.DataFrame)
        assert len(links_df) == 7
        assert all(
            col in links_df.columns
            for col in ["source", "target", "value", "min", "max", "aggregate"]
        )
        assert fig.layout.title.text == "Test Sankey"

    def test_mean_aggregation(self, sample_flows_df):
        fig, links_df = graphs.sankey(sample_flows_df, agg="mean")

        assert isinstance(fig, go.Figure)
        np.testing.assert_array_almost_equal(
            links_df["value"].values, sample_flows_df.mean(axis=0).values
        )

    def test_max_aggregation(self, sample_flows_df):
        fig, links_df = graphs.sankey(sample_flows_df, agg="max")

        assert isinstance(fig, go.Figure)
        np.testing.assert_array_almost_equal(
            links_df["value"].values, sample_flows_df.max(axis=0).values
        )

    def test_with_row_index_int(self, sample_flows_df):
        fig, links_df = graphs.sankey(sample_flows_df, row=5)

        assert isinstance(fig, go.Figure)
        np.testing.assert_array_almost_equal(
            links_df["value"].values, sample_flows_df.iloc[5].values
        )
        assert "timestamp" in links_df.columns

    def test_with_row_index_label(self, sample_flows_df):
        row_label = sample_flows_df.index[10]

        fig, links_df = graphs.sankey(sample_flows_df, row=row_label)

        assert isinstance(fig, go.Figure)
        np.testing.assert_array_almost_equal(
            links_df["value"].values, sample_flows_df.loc[row_label].values
        )

    def test_drop_zero_links(self, flows_with_zeros):
        fig, links_df = graphs.sankey(flows_with_zeros, drop_zero_links=True)

        assert isinstance(fig, go.Figure)
        # Only source1 and source3 carry energy.
        assert len(links_df) == 2
        assert all(links_df["value"] != 0)

    def test_keep_zero_links(self, flows_with_zeros):
        fig, links_df = graphs.sankey(flows_with_zeros, drop_zero_links=False)

        assert isinstance(fig, go.Figure)
        assert len(links_df) == 3
        # Zero values are replaced by a tiny positive number.
        assert any(links_df["value"] == 1e-9)

    def test_with_energy_system(self, sample_flows_df, sample_energy_system):
        fig, _ = graphs.sankey(sample_flows_df, es=sample_energy_system)

        assert isinstance(fig, go.Figure)
        assert fig.data[0].node.color is not None

    def test_invalid_multiindex(self):
        df = pd.DataFrame({"col1": [1, 2, 3]})

        with pytest.raises(TypeError, match="must be a pandas MultiIndex"):
            graphs.sankey(df)

    def test_invalid_column_levels(self):
        columns = pd.MultiIndex.from_tuples(
            [("a", "b", "c")], names=["l1", "l2", "l3"]
        )
        df = pd.DataFrame([[1]], columns=columns)

        with pytest.raises(ValueError, match="exactly 2 column levels"):
            graphs.sankey(df)

    def test_empty_dataframe(self, empty_flows_df):
        with pytest.raises(ValueError, match="Input DataFrame is empty"):
            graphs.sankey(empty_flows_df)

    def test_invalid_aggregation(self, sample_flows_df):
        with pytest.raises(ValueError, match="agg must be one of"):
            graphs.sankey(sample_flows_df, agg="invalid")

    def test_all_zeros_with_drop(self):
        df = _single_link_flows(periods=5, value=0.0)

        with pytest.raises(
            ValueError, match="No links remain after filtering"
        ):
            graphs.sankey(df, drop_zero_links=True)

    def test_hover_template_without_row(self, sample_flows_df):
        fig, _ = graphs.sankey(sample_flows_df)

        hover = fig.data[0].link.hovertemplate
        assert "Min:" in hover
        assert "Max:" in hover
        assert "Aggregate:" in hover
        assert "Timestamp:" not in hover

    def test_hover_template_with_row(self, sample_flows_df):
        fig, _ = graphs.sankey(sample_flows_df, row=0)

        hover = fig.data[0].link.hovertemplate
        assert "Timestamp:" in hover
        assert "Min:" in hover
        assert "Max:" in hover

    @pytest.mark.parametrize("agg_method", ["sum", "mean", "max"])
    def test_all_aggregations(self, sample_flows_df, agg_method):
        fig, links_df = graphs.sankey(sample_flows_df, agg=agg_method)

        assert isinstance(fig, go.Figure)
        assert not links_df.empty

    @pytest.mark.parametrize("row_selector", [0, 5, 10, 15, 20])
    def test_different_rows(self, sample_flows_df, row_selector):
        fig, links_df = graphs.sankey(sample_flows_df, row=row_selector)

        assert isinstance(fig, go.Figure)
        np.testing.assert_array_almost_equal(
            links_df["value"].values,
            sample_flows_df.iloc[row_selector].values,
        )

    def test_full_workflow(self, sample_flows_df, sample_energy_system):
        fig, links_df = graphs.sankey(
            sample_flows_df,
            es=sample_energy_system,
            title="Integration Test",
            row=None,
            agg="sum",
            drop_zero_links=False,
        )

        assert isinstance(fig, go.Figure)
        assert isinstance(links_df, pd.DataFrame)
        assert fig.layout.title.text == "Integration Test"
        assert len(links_df) == 7
        assert all(
            col in links_df.columns
            for col in ["source", "target", "value", "min", "max", "aggregate"]
        )

    def test_single_link(self):
        fig, links_df = graphs.sankey(_single_link_flows(5, 10.0))

        assert isinstance(fig, go.Figure)
        assert len(links_df) == 1

    def test_large_values(self):
        fig, links_df = graphs.sankey(_single_link_flows(10, 1e9))

        assert isinstance(fig, go.Figure)
        assert links_df["value"].iloc[0] > 1e8

    def test_small_values(self):
        fig, links_df = graphs.sankey(_single_link_flows(10, 1e-6))

        assert isinstance(fig, go.Figure)
        assert links_df["value"].iloc[0] > 0

    @pytest.mark.parametrize("drop_zeros", [True, False])
    def test_complex_data(self, complex_flows_df, drop_zeros):
        fig, links_df = graphs.sankey(
            complex_flows_df, drop_zero_links=drop_zeros
        )

        assert isinstance(fig, go.Figure)
        assert len(links_df) > 0
        if drop_zeros:
            assert all(links_df["value"] > 0)


def test_sankey_diagram():
    energy_system = dp_energy_system.create_energy_system_from_dp(
        TEST_DATA / "openPlan_package"
    )
    results = optimise(energy_system)

    fig, _ = graphs.sankey(results["flow"], es=energy_system)
    actual_data = fig.to_dict()["data"][0]

    assert actual_data["type"] == "sankey"
    assert len(actual_data["node"]["label"]) == 8
    assert len(actual_data["link"]["source"]) == 8
    assert all(v >= 0 for v in actual_data["link"]["value"])

    total_flow = sum(actual_data["link"]["value"])
    expected_total_flow = 730.5401400484004
    assert abs(total_flow - expected_total_flow) < 1e-6


# ---------------------------------------------------------------------------
# capacities_graph
# ---------------------------------------------------------------------------


class TestCapacitiesGraph:
    """Tests for capacities_graph()."""

    def test_basic(self, sample_results, sample_energy_system):
        fig = graphs.capacities_graph(
            sample_results["invest"], sample_energy_system
        )

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2
        assert fig.data[0].name == "Installed capacity"
        assert fig.data[1].name == "Optimized capacity"
        assert fig.layout.title.text == "Installed vs Optimized Capacity"

    def test_values(self, sample_results, sample_energy_system):
        fig = graphs.capacities_graph(
            sample_results["invest"], sample_energy_system
        )

        optimized_trace = fig.data[1]
        assert sorted(optimized_trace.x) == ["Batterie", "pv", "wind"]
        assert optimized_trace.y.min() == 0
        assert round(optimized_trace.y.max(), 7) == 1.0107436

    def test_no_optimized_capacity(self, sample_energy_system):
        """Components missing in the invest table get a capacity of 0."""
        columns = pd.MultiIndex.from_tuples(
            [("component1", "invest"), ("component2", "invest")]
        )
        invest_df = pd.DataFrame([[50.0, 75.0]], columns=columns)

        fig = graphs.capacities_graph(invest_df, sample_energy_system)

        assert isinstance(fig, go.Figure)
        assert 0.0 in fig.data[1].y

    def test_layout(self, sample_results, sample_energy_system):
        fig = graphs.capacities_graph(
            sample_results["invest"], sample_energy_system
        )

        assert fig.layout.barmode == "stack"
        assert fig.layout.xaxis.title.text == "Component"
        assert fig.layout.yaxis.title.text == "Capacity"
        assert fig.layout.margin.b == 150

    def test_marker_style(self, sample_results, sample_energy_system):
        fig = graphs.capacities_graph(
            sample_results["invest"], sample_energy_system
        )

        # Installed capacity is hatched, optimized capacity is solid.
        assert fig.data[0].marker.color == "#d64e12"
        assert fig.data[0].marker.pattern.shape == "x"
        assert fig.data[1].marker.color == "#d64e12"

    def test_empty_nodes(self, sample_results):
        """Nodes without ``installed_capacity`` yield empty traces."""
        es = Mock()
        es.nodes = [Mock(spec=["label"])]

        fig = graphs.capacities_graph(sample_results["invest"], es)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2

    def test_all_zeros(self, sample_energy_system):
        columns = pd.MultiIndex.from_tuples(
            [("component1", "invest"), ("component2", "invest")]
        )
        invest_df = pd.DataFrame([[0.0, 0.0]], columns=columns)

        fig = graphs.capacities_graph(invest_df, sample_energy_system)

        assert isinstance(fig, go.Figure)

    def test_full_workflow(self, sample_results, sample_energy_system):
        fig = graphs.capacities_graph(
            sample_results["invest"], sample_energy_system
        )

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2
        assert fig.layout.barmode == "stack"
        assert sorted(fig.data[0].x) == ["Batterie", "pv", "wind"]

    def test_simple_script(self, simple_script_result):
        res, esys = simple_script_result

        fig = graphs.capacities_graph(res["invest"], esys)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2


# ---------------------------------------------------------------------------
# capacities
# ---------------------------------------------------------------------------


def test_capacities_shows_installed_or_optimized_components_with_costs():
    bus = CarrierBus(name="electricity")
    wind = _N("wind", capex_spec=1100, opex_spec=10, installed_capacity=None)
    pv = _N("pv", capex_spec=600, opex_spec=0, installed_capacity=2)
    battery = _N("battery", capex_spec=0, opex_spec=5)
    legacy = _N("legacy", capex_spec=0, opex_spec=0, installed_capacity=5)
    idle = _N("idle", capex_spec=600, opex_spec=0)
    noise = _N("noise", capex_spec=600, opex_spec=0)
    free = _N("free", capex_spec=0, opex_spec=0)
    commodity = _N("rgas")
    es_stub = SimpleNamespace(
        nodes=[bus, wind, pv, battery, legacy, idle, noise, free, commodity]
    )
    imported = {
        "invest": pd.DataFrame(
            [{"wind": 390.0, "battery": 8000.0, "noise": 1e-10, "free": 5.0}]
        ),
    }

    fig = graphs.capacities(imported, es_stub)

    assert len(fig.data) == 2
    assert fig.data[0].name == "Installed"
    assert fig.data[1].name == "Optimized"
    assert list(fig.data[0].x) == ["wind", "pv", "battery", "legacy"]
    assert list(fig.data[0].y) == [None, 2.0, None, 5.0]
    assert list(fig.data[1].y) == [390.0, None, 8000.0, None]
    assert list(fig.data[0].customdata) == [None, "2.0", None, "5.0"]
    assert list(fig.data[1].customdata) == ["390.0", None, "8 000.0", None]


def test_capacities_without_investments():
    pv = _N("pv", capex_spec=600, opex_spec=0, installed_capacity=2)
    idle = _N("idle", capex_spec=600, opex_spec=0)
    es_stub = SimpleNamespace(nodes=[pv, idle])

    fig = graphs.capacities({"invest": pd.DataFrame()}, es_stub)

    assert len(fig.data) == 2
    assert list(fig.data[0].x) == ["pv"]
    assert list(fig.data[0].y) == [2.0]
    assert list(fig.data[1].y) == [None]


def test_storage_exposes_cost_and_installed_capacity(simple_script_result):
    _, esys = simple_script_result
    battery = next(node for node in esys.nodes if node.label == "Batterie")

    assert battery.capex_spec == 3.0
    assert battery.opex_spec == 5.0
    assert battery.installed_capacity == 1000


def test_capacities_shows_installed_storage(simple_script_result):
    res, esys = simple_script_result

    fig = graphs.capacities({"invest": res["invest"]}, esys)

    installed = dict(zip(fig.data[0].x, fig.data[0].y, strict=True))
    assert installed["Batterie"] == 1000


# ---------------------------------------------------------------------------
# compare_capacities
# ---------------------------------------------------------------------------


def _capacity_scenario(nodes, invest=None, mapping=None):
    results = {"component_type_mapping": mapping or {}}
    if invest is not None:
        results["invest"] = pd.DataFrame([invest])
    return results, SimpleNamespace(nodes=nodes)


def test_compare_capacities_groups_by_type():
    scenario1 = _capacity_scenario(
        [
            FakeWindTurbine(
                "wind", capex_spec=1100, opex_spec=10, installed_capacity=None
            ),
            FakePvPlant(
                "pv", capex_spec=600, opex_spec=0, installed_capacity=2
            ),
            FakeWindTurbine("noise", capex_spec=600, opex_spec=0),
        ],
        invest={"wind": 390.0, "noise": 1e-10},
        mapping={"wind": "wind_turbine", "pv": "pv_plant"},
    )
    scenario2 = _capacity_scenario(
        [FakeWindTurbine("windplant", capex_spec=1000, opex_spec=0)],
        invest={"windplant": 7.0},
        mapping={"windplant": "wind_turbine"},
    )

    fig = graphs.compare_capacities({"s1": scenario1, "s2": scenario2})

    assert [trace.name for trace in fig.data] == [
        "s1",
        "s1",
        "s2",
        "Installed",
        "Optimized",
    ]
    assert [trace.showlegend for trace in fig.data] == [
        True,
        False,
        True,
        True,
        True,
    ]
    assert list(fig.data[0].x) == [0]
    assert list(fig.data[0].y) == [2.0]
    assert list(fig.data[1].x) == [2]
    assert list(fig.data[1].y) == [390.0]
    assert list(fig.data[2].x) == [3]
    assert list(fig.data[2].y) == [7.0]
    assert list(fig.layout.xaxis.tickvals) == [0, 2, 3]
    assert list(fig.layout.xaxis.ticktext) == ["pv", "wind", "windplant"]
    assert fig.data[0].marker.pattern.shape == "x"
    assert fig.data[1].marker.pattern.shape is None
    assert "Installed capacity" in fig.data[0].hovertemplate
    assert "Optimized capacity" in fig.data[1].hovertemplate
    assert fig.data[0].marker.color == "#636EFA"
    assert fig.data[2].marker.color == "#EF553B"


def test_compare_capacities_without_bars_only_has_legend_entries():
    fig = graphs.compare_capacities({"s": _capacity_scenario([])})

    assert [trace.name for trace in fig.data] == ["Installed", "Optimized"]
    assert fig.layout.xaxis.tickvals is None


def test_compare_capacities_validates_input():
    with pytest.raises(ValueError, match="at least one scenario"):
        graphs.compare_capacities({})
    with pytest.raises(ValueError, match=r"\(results, es\) pair"):
        graphs.compare_capacities({"s": ({},)})


# ---------------------------------------------------------------------------
# plot_timeseries
# ---------------------------------------------------------------------------


def _timeseries_system():
    bus = CarrierBus(name="bus")
    other = CarrierBus(name="other")
    idle_bus = CarrierBus(name="idle_bus")
    pv, load, idle = _N("pv"), _N("load"), _N("idle")
    pv2, load2 = _N("pv2"), _N("load2")
    index = pd.date_range("2023-01-01", periods=3, freq="h")
    flows = pd.DataFrame(
        np.array(
            [
                [1.0, 2.0, 3.0],  # pv -> bus
                [1.0, 1.0, 1.0],  # bus -> load
                [0.0, 0.0, 0.0],  # idle -> bus (no energy)
                [5.0, 5.0, 5.0],  # bus -> bus (loop)
                [2.0, 2.0, 2.0],  # pv2 -> other
                [1.0, 1.0, 1.0],  # other -> load2
            ]
        ).T,
        index=index,
        columns=pd.MultiIndex.from_tuples(
            [
                (pv, bus),
                (bus, load),
                (idle, bus),
                (bus, bus),
                (pv2, other),
                (other, load2),
            ]
        ),
    )
    es = SimpleNamespace(nodes=[bus, pv, other, idle_bus])
    return bus, other, flows, es


def test_plot_timeseries_dropdown_and_traces():
    bus, other, flows, es = _timeseries_system()

    fig = graphs.plot_timeseries({"flow": flows}, es)

    buttons = fig.layout.updatemenus[0].buttons
    assert [b.label for b in buttons] == [
        graphs._facade_label(bus),
        graphs._facade_label(other),
    ]
    assert [t.name for t in fig.data] == [
        "from pv",
        "to load",
        "from pv2",
        "to load2",
    ]
    # Only the traces of the first bus are visible at the start.
    assert [t.visible for t in fig.data] == [True, True, False, False]
    assert fig.layout.title.text == (
        f"Energy flows in {graphs._facade_label(bus)}"
    )


def test_plot_timeseries_threshold_omits_small_flows():
    _, _, flows, es = _timeseries_system()

    fig = graphs.plot_timeseries(flows, es, threshold=3.0)

    assert [t.name for t in fig.data] == ["from pv", "from pv2"]


def test_plot_timeseries_without_flows_raises():
    es = SimpleNamespace(nodes=[CarrierBus(name="bus")])

    with pytest.raises(ValueError, match="No bus flows"):
        graphs.plot_timeseries(pd.DataFrame({"a": [1.0]}), es)


# ---------------------------------------------------------------------------
# plot_energy_mix
# ---------------------------------------------------------------------------


def test_plot_energy_mix_values_and_period():
    bus = CarrierBus(name="bus")
    grid, wind, tiny = _source("grid"), _source("wind"), _source("tiny")
    ghost = _source("ghost")
    es = SimpleNamespace(nodes=[bus, grid, wind, tiny])
    flows = _flows(
        [(grid, bus), (wind, bus), (tiny, bus), (ghost, bus)],
        [[3000.0, 2000.0, 0.05, 9000.0]],
        index=pd.DatetimeIndex(["2023-01-01"]),
    )

    fig = graphs.plot_energy_mix({"flow": flows}, es)

    assert list(fig.data[0].labels) == [
        graphs._facade_label(grid),
        graphs._facade_label(wind),
    ]
    assert list(fig.data[0].values) == [3.0, 2.0]
    assert "from 2023-01-01 to 2023-01-01" in fig.layout.title.text


def test_plot_energy_mix_unit_and_plain_index():
    bus = CarrierBus(name="bus")
    grid = _source("grid")
    flows = _flows([(grid, bus)], [[3e6]])

    fig = graphs.plot_energy_mix(
        flows, SimpleNamespace(nodes=[grid]), unit="GWh"
    )

    assert list(fig.data[0].values) == [3.0]
    assert fig.layout.title.text == "Accumulated energy supply of the system"


def test_plot_energy_mix_without_supply_logs_error(caplog):
    # No (source, target) columns.
    flows = pd.DataFrame({"a": [1.0]})

    with caplog.at_level(logging.ERROR):
        fig = graphs.plot_energy_mix(
            flows, SimpleNamespace(nodes=[_source("grid")])
        )

    assert len(fig.data) == 0
    assert "No energy supply found" in caplog.text


# ---------------------------------------------------------------------------
# plot_renewable_vs_nonrenewable
# ---------------------------------------------------------------------------


def test_plot_renewable_vs_nonrenewable():
    grid = _source("grid")
    grid.renewable_share = 0.4
    wind = _source("wind", renewable_asset=True)
    gas = _source("gas", renewable_asset=False)
    bus = CarrierBus(name="bus")
    flows = pd.DataFrame(
        [[100.0, 50.0, 25.0]],
        columns=pd.MultiIndex.from_tuples(
            [(grid, bus), (wind, bus), (gas, bus)]
        ),
    )
    es_stub = SimpleNamespace(nodes=[grid, wind, gas])

    fig = graphs.plot_renewable_vs_nonrenewable(
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


def test_plot_renewable_vs_nonrenewable_without_renewable_supply():
    bus = CarrierBus(name="bus")
    gas = _source("gas", renewable_asset=False)
    flows = _flows([(gas, bus)], [[25.0]])

    fig = graphs.plot_renewable_vs_nonrenewable(
        flows, SimpleNamespace(nodes=[gas]), threshold=0, unit="Wh"
    )

    texts = [annotation.text for annotation in fig.layout.annotations]
    assert "No energy supply" in texts
    assert "Total<br>25.0 Wh" in texts
    assert fig.layout.yaxis.range[1] == pytest.approx(28.0)
    assert fig.layout.title.text == "Renewable vs non-renewable energy supply"


def test_plot_renewable_vs_nonrenewable_period_and_results_dict():
    bus = CarrierBus(name="bus")
    wind = _source("wind", renewable_asset=True)
    ghost = _source("ghost", renewable_asset=True)
    flows = _flows(
        [(wind, bus), (ghost, bus)],
        [[5000.0, 1000.0]],
        index=pd.DatetimeIndex(["2023-01-01"]),
    )

    fig = graphs.plot_renewable_vs_nonrenewable(
        {"flow": flows}, SimpleNamespace(nodes=[wind])
    )

    assert "from 2023-01-01 to 2023-01-01" in fig.layout.title.text
    assert [trace.y[0] for trace in fig.data] == [5.0]


def test_plot_renewable_vs_nonrenewable_without_supply_logs_error(caplog):
    with caplog.at_level(logging.ERROR):
        fig = graphs.plot_renewable_vs_nonrenewable(
            pd.DataFrame({"a": [1.0]}),
            SimpleNamespace(nodes=[_source("grid")]),
        )

    assert len(fig.data) == 0
    assert "No energy supply found" in caplog.text


# ---------------------------------------------------------------------------
# plot_annual_costs / compare_annual_costs
# ---------------------------------------------------------------------------


def test_plot_annual_costs(monkeypatch):
    table = pd.DataFrame(
        {
            "Component": ["component_a", "component_b", "total"],
            "Annualized investment cost": [10.0, -5.0, 5.0],
            "Fix operational costs": [2.0, 1.0, 3.0],
            "Dispatch costs": [3.0, -2.0, 1.0],
            "total": [15.0, -6.0, 9.0],
        }
    )

    def fake_yearly_project_costs(results, es):
        results["eesyplan"] = {"yearly_project_costs": table}

    monkeypatch.setattr(
        "oemof.eesyplan.postprocessing.graphs.yearly_project_costs",
        fake_yearly_project_costs,
    )

    fig = graphs.plot_annual_costs({}, None)

    assert fig.layout.barmode == "relative"
    assert [trace.name for trace in fig.data] == [
        "Annualized investment cost",
        "Fix operational costs",
        "Dispatch costs",
    ]
    for trace in fig.data:
        assert list(trace.x) == ["component_a", "component_b"]


def test_compare_annual_costs(monkeypatch):
    # The class names matter: the graph groups the bars by them.
    class WindTurbine:
        def __init__(self, label):
            self.label = label
            self.parent = None

    class PvPlant:
        def __init__(self, label):
            self.label = label
            self.parent = None

    wind1 = WindTurbine("wind1")
    wind2 = WindTurbine("wind2")
    pv1 = PvPlant("pv1")
    windplant = WindTurbine("windplant")

    table1 = pd.DataFrame(
        {
            "Component": ["wind1", "wind2", "pv1", "total"],
            "Annualized investment cost": [10.0, 20.0, 5.0, 35.0],
            "Fix operational costs": [1.0, 2.0, 0.5, 3.5],
            "Dispatch costs": [0.1, 0.2, 0.05, 0.35],
        }
    )
    table2 = pd.DataFrame(
        {
            "Component": ["windplant", "total"],
            "Annualized investment cost": [7.0, 7.0],
            "Fix operational costs": [0.7, 0.7],
            "Dispatch costs": [0.07, 0.07],
        }
    )
    es1 = SimpleNamespace(nodes=[wind1, wind2, pv1])
    es1.table = table1
    es2 = SimpleNamespace(nodes=[windplant])
    es2.table = table2

    def fake_yearly_project_costs(results, es):
        results["eesyplan"] = {"yearly_project_costs": es.table}

    monkeypatch.setattr(
        "oemof.eesyplan.postprocessing.graphs.yearly_project_costs",
        fake_yearly_project_costs,
    )

    fig = graphs.compare_annual_costs(
        {"scenario1": ({}, es1), "scenario2": ({}, es2)}
    )

    scenario_traces = [t for t in fig.data if "scenario" in t.name]
    assert fig.layout.barmode == "relative"
    assert [t.name for t in scenario_traces] == (
        ["scenario1"] * 3 + ["scenario2"] * 3
    )
    assert [t.showlegend for t in scenario_traces] == [True, False, False] * 2
    assert [t.legendgroup for t in scenario_traces] == (
        ["scenario1"] * 3 + ["scenario2"] * 3
    )
    # pv1 forms its own type group, the wind turbines sit together
    # behind the gap.
    assert list(fig.layout.xaxis.tickvals) == [0, 2, 3, 4]
    assert list(fig.layout.xaxis.ticktext) == [
        "pv1",
        "wind1",
        "wind2",
        "windplant",
    ]
    assert list(fig.data[0].x) == [0, 2, 3]
    assert list(fig.data[0].y) == [5.0, 10.0, 20.0]
    assert list(fig.data[3].x) == [4]
    assert list(fig.data[3].y) == [7.0]
    assert list(fig.data[0].customdata) == [
        ["pv1", "PvPlant", "5"],
        ["wind1", "WindTurbine", "10"],
        ["wind2", "WindTurbine", "20"],
    ]
    assert fig.data[0].marker.color == "#636EFA"
    assert fig.data[3].marker.color == "#EF553B"
    assert fig.data[1].marker.pattern.shape == "x"
    assert fig.data[2].marker.pattern.shape == "/"
    assert "Scenario: scenario1" in fig.data[0].hovertemplate


def test_compare_annual_costs_validates_input():
    with pytest.raises(ValueError, match="at least one scenario"):
        graphs.compare_annual_costs({})

    with pytest.raises(ValueError, match=r"\(results, es\) pair"):
        graphs.compare_annual_costs({"scenario1": ({},)})
