"""Tests for oemof.eesyplan.dashboard.dashboard."""

import importlib.util
import json
import logging
import runpy
import shutil
import sys
import zipfile
from pathlib import Path

import dash
import pandas as pd
import plotly.graph_objects as go
import pytest
from dash import dash_table
from dash import dcc

from oemof.eesyplan import CarrierBus
from oemof.eesyplan import import_results
from oemof.eesyplan.dashboard import DashboardResults
from oemof.eesyplan.dashboard import dashboard
from oemof.eesyplan.dashboard import prepare_dash_app
from oemof.eesyplan.datapackage.energy_system import (
    create_energy_system_from_dp,
)
from oemof.eesyplan.datapackage.energy_system import (
    get_component_type_mapping_from_dp,
)

TEST_DATA = Path(__file__).parent / "test_data"
SCENARIO_PATH = TEST_DATA / "openPlan_package"
SCENARIO_JSON = SCENARIO_PATH / "datapackage.json"
RESULTS_PATH = TEST_DATA / "openPlan_results_package"
YEAR0_COLUMN = "Investment cost in year 0 (not including reinvestment)"


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def energy_system():
    return create_energy_system_from_dp(SCENARIO_PATH)


@pytest.fixture
def imported_results(energy_system):
    return import_results(path=RESULTS_PATH, es=energy_system)


@pytest.fixture
def results(imported_results, energy_system):
    return DashboardResults(imported_results, energy_system)


@pytest.fixture
def example_fig():
    return go.Figure(data=[go.Scatter(x=[1, 2, 3], y=[4, 5, 6], mode="lines")])


@pytest.fixture
def dash_results(results, example_fig, monkeypatch):
    """Dashboard results whose capacities graph needs no real data."""
    results._data.setdefault("invest", pd.DataFrame())
    monkeypatch.setattr(
        dashboard.graphs, "capacities_graph", lambda invest, es: example_fig
    )
    return results


@pytest.fixture
def sankey_calls(monkeypatch):
    """Replace ``sankey_to_json`` by a recorder and return its rows."""
    rows = []

    def fake_sankey_to_json(results, row=None):
        rows.append(row)
        return {"data": [], "layout": {"title": {"text": f"row {row}"}}}

    monkeypatch.setattr(dashboard, "sankey_to_json", fake_sankey_to_json)
    return rows


def _iter_components(component):
    """Yield a Dash component and every component below it."""
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    if not isinstance(children, list | tuple):
        children = [children]
    for child in children:
        yield from _iter_components(child)


def _find_component(app, component_id):
    for component in _iter_components(app.layout):
        if getattr(component, "id", None) == component_id:
            return component
    return None


def _callback_function(app, callback_id):
    """Return the plain function behind a registered Dash callback."""
    return app.callback_map[callback_id]["callback"].__wrapped__


def _export_dashboard_resources(results, path):
    """Export the dashboard folder and return the listed resources."""
    results._export_results_to_dir(path, dashboard=True)
    with (path / "datapackage.json").open(encoding="utf-8") as file:
        return json.load(file)["resources"]


def _fake_calculate_all_kpis(results, es):
    """Write small KPI tables instead of running the real calculation."""
    kpis = dashboard._eesyplan_kpis(results)
    kpis["yearly_project_costs"] = pd.DataFrame(
        {
            "Component": ["a", "b", "total"],
            "Fix operational costs": [1.0, 2.0, 3.0],
        }
    )
    kpis["project_cost_table"] = pd.DataFrame(
        {
            "Component": ["a", "b", "total"],
            YEAR0_COLUMN: [10.0, 20.0, 30.0],
        }
    )
    kpis["lcoe"] = 0.25
    kpis["renewable_share"] = 0.5


# ---------------------------------------------------------------------------
# DashboardResults: storing results
# ---------------------------------------------------------------------------


def test_dashboard_results_initialization(imported_results, energy_system):
    results = DashboardResults(imported_results, energy_system)

    assert results.energy_system is energy_system
    assert results._core_keys == set(imported_results.keys())
    assert results.figure_keys == []
    assert results.table_keys == []


def test_add_extra_key(results):
    results["extra"] = {"adict": 123}

    assert "extra" in results.keys()
    assert "extra" not in results._core_keys
    assert results["extra"] == {"adict": 123}
    assert results.get("extra") == {"adict": 123}


def test_get_missing_key_returns_default(results):
    assert results.get("does_not_exist") is None
    assert results.get("does_not_exist", 42) == 42


def test_assign_plotly_figure(results, example_fig):
    results["plotly_fig"] = example_fig.to_plotly_json()

    stored_figure = results["plotly_fig"]
    assert isinstance(stored_figure, dict)
    assert stored_figure["data"][0]["type"] == "scatter"
    assert list(stored_figure["data"][0]["x"]) == [1, 2, 3]
    assert list(stored_figure["data"][0]["y"]) == [4, 5, 6]


def test_core_key_cannot_be_overwritten(results):
    core_key = next(iter(results._core_keys))

    with pytest.raises(KeyError, match="is not overwritable"):
        results[core_key] = {}


@pytest.mark.parametrize("value", [42, "text", [1, 2]])
def test_setitem_rejects_unsupported_values(results, value):
    with pytest.raises(TypeError, match="not a dataframe or a dict"):
        results["extra"] = value

    assert results.get("extra") is None


def test_reassigning_extra_key_keeps_first_value(results):
    results["extra"] = {"version": 1}

    results["extra"] = {"version": 2}

    # Current behaviour: only core keys raise an error. Any other existing
    # key is silently left unchanged.
    assert results["extra"] == {"version": 1}


def test_pop(results):
    results["extra"] = {"a": 1}

    assert results.pop("extra") == {"a": 1}
    assert results.get("extra") is None
    assert results.pop("extra", "default") == "default"


def test_autoassign_keys_registers_extra_keys_once(results):
    results["fig"] = {"data": []}
    results["table"] = pd.DataFrame({"a": [1]})

    results.autoassign_keys()
    results.autoassign_keys()

    assert results.figure_keys == ["fig"]
    assert results.table_keys == ["table"]


# ---------------------------------------------------------------------------
# DashboardResults: figures and tables
# ---------------------------------------------------------------------------


def test_figures_returns_registered_figures(results):
    fig_1 = {"data": [{"x": [1, 2]}]}
    fig_2 = {"data": [{"x": [3, 4]}]}
    results["fig_1"] = fig_1
    results["fig_2"] = fig_2
    results["other"] = {"foo": "bar"}
    results.figure_keys.extend(["fig_1", "fig_2"])

    assert results.figures() == {"fig_1": fig_1, "fig_2": fig_2}
    assert results.figures(["fig_1"]) == {"fig_1": fig_1}
    # Unknown keys are ignored.
    assert results.figures(["fig_1", "does_not_exist"]) == {"fig_1": fig_1}


def test_tables_returns_registered_tables(results):
    table_1 = pd.DataFrame({"a": [1, 2]})
    results["table_1"] = table_1
    results["table_2"] = pd.DataFrame({"b": [3]})
    results.table_keys.extend(["table_1", "table_2"])

    assert list(results.tables()) == ["table_1", "table_2"]
    assert list(results.tables(["table_2", "unknown"])) == ["table_2"]
    pd.testing.assert_frame_equal(
        results.tables(["table_1"])["table_1"], table_1
    )


def test_tables_convert_to_json(results):
    results["df_table"] = pd.DataFrame({"a": [1, 2]})
    results["dict_table"] = {"total": 1.5}
    results.table_keys.extend(["df_table", "dict_table"])

    tables = results.tables(convert_to_json=True)

    assert tables == {
        "df_table": {"a": {"0": 1, "1": 2}},
        "dict_table": {"total": 1.5},
    }


def test_tables_json_rejects_unsupported_type(results):
    results._data["bad"] = 5
    results.table_keys.append("bad")

    with pytest.raises(TypeError, match="should either be dict"):
        results.tables(convert_to_json=True)


def test_add_capacities_graph(dash_results):
    key = dash_results.add_capacities_graph()

    assert key == "capacities"
    assert key in dash_results.figure_keys
    figure = dash_results[key]
    assert figure["data"][0]["type"] == "scatter"
    assert figure["data"][0]["x"] == [1, 2, 3]


def test_add_all_figures(results, monkeypatch):
    monkeypatch.setattr(
        dashboard,
        "FIGURES",
        {
            "fig_a": lambda res: {"data": [1]},
            "fig_b": lambda res: {"data": [2]},
        },
    )

    results.add_all_figures()

    assert results.figure_keys == ["fig_a", "fig_b"]
    assert results["fig_b"] == {"data": [2]}


def test_add_all_tables_summarises_kpis(results, monkeypatch):
    monkeypatch.setattr(
        dashboard, "calculate_all_kpis", _fake_calculate_all_kpis
    )
    results._data["variable_costs"] = pd.DataFrame({"a": [5.0, 7.0]})

    results.add_all_tables()

    assert results["summary"] == {
        "total_cost_year0": 30.0,
        "total_yearly_fixed_costs": 3.0,
        "total_dispatch_costs": 12.0,
        "lcoe": 0.25,
        "renewable_share": 0.5,
    }
    assert results.table_keys == [
        "summary",
        "yearly_project_costs",
        "project_cost_table",
    ]
    assert isinstance(results["yearly_project_costs"], pd.DataFrame)
    # The temporary KPI namespace is removed again.
    assert results.get("eesyplan") is None


def test_add_all_tables_without_variable_costs(results, monkeypatch):
    monkeypatch.setattr(
        dashboard, "calculate_all_kpis", _fake_calculate_all_kpis
    )
    results._data.pop("variable_costs", None)

    results.add_all_tables()

    assert results["summary"]["total_dispatch_costs"] == 0.0


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------


def _tuple_columns_frame():
    """Frame whose columns are plain tuples (not a MultiIndex)."""
    columns = pd.Index([("a", "b"), ("c", "d")], tupleize_cols=False)
    return pd.DataFrame([[1.0, 2.0]], columns=columns)


def test_normalize_df_names_unnamed_index_and_copies():
    frame = pd.DataFrame({"a": [1]})

    result = dashboard._normalize_df_for_csv(frame, "any")

    assert result.index.name == "index"
    assert frame.index.name is None


def test_normalize_df_keeps_existing_index_name():
    frame = pd.DataFrame({"a": [1]}, index=pd.Index([0], name="time"))

    result = dashboard._normalize_df_for_csv(frame, "any")

    assert result.index.name == "time"


def test_normalize_df_converts_variable_cost_tuples_to_multiindex():
    frame = _tuple_columns_frame()
    assert not isinstance(frame.columns, pd.MultiIndex)

    result = dashboard._normalize_df_for_csv(frame, "variable_costs")

    assert isinstance(result.columns, pd.MultiIndex)
    assert list(result.columns.names) == ["from", "to"]
    assert list(result.columns) == [("a", "b"), ("c", "d")]


def test_normalize_df_only_converts_variable_costs():
    result = dashboard._normalize_df_for_csv(_tuple_columns_frame(), "flow")

    assert not isinstance(result.columns, pd.MultiIndex)


def test_normalize_df_keeps_plain_variable_cost_columns():
    frame = pd.DataFrame([[1.0, 2.0]], columns=["a", "b"])

    result = dashboard._normalize_df_for_csv(frame, "variable_costs")

    assert list(result.columns) == ["a", "b"]


def test_normalize_df_keeps_existing_multiindex():
    columns = pd.MultiIndex.from_tuples([("a", "b")], names=["x", "y"])
    frame = pd.DataFrame([[1.0]], columns=columns)

    result = dashboard._normalize_df_for_csv(frame, "variable_costs")

    assert list(result.columns.names) == ["x", "y"]


def test_export_df_resource_writes_sequence_for_datetime_index(tmp_path):
    index = pd.date_range("2023-01-01", periods=2, freq="h")
    frame = pd.DataFrame({"a": [1.0, 2.0]}, index=index)
    resources = []

    dashboard._export_df_resource(frame, "flow", tmp_path, resources)

    assert (tmp_path / "sequences" / "flow.csv").exists()
    assert resources == [
        {
            "name": "flow",
            "path": "results/sequences/flow.csv",
            "kind": "sequence",
            "format": "csv",
            "dialect": {"header": True, "headerRows": [0]},
        }
    ]


def test_export_df_resource_writes_element_with_multiindex_header(tmp_path):
    columns = pd.MultiIndex.from_tuples([("a", "b")], names=["from", "to"])
    frame = pd.DataFrame([[1.0]], columns=columns)
    resources = []

    dashboard._export_df_resource(frame, "costs", tmp_path, resources)

    assert (tmp_path / "elements" / "costs.csv").exists()
    assert resources[0]["kind"] == "element"
    assert resources[0]["dialect"]["headerRows"] == [0, 1]


def test_to_dataframe_converts_supported_values():
    frame = pd.DataFrame({"a": [1]})

    copied = dashboard._to_dataframe(frame)

    assert copied is not frame
    pd.testing.assert_frame_equal(copied, frame)
    pd.testing.assert_frame_equal(
        dashboard._to_dataframe(pd.Series([1, 2], name="s")),
        pd.DataFrame({"s": [1, 2]}),
    )
    pd.testing.assert_frame_equal(
        dashboard._to_dataframe({"x": [1, 2]}),
        pd.DataFrame({"x": [1, 2]}),
    )


def test_to_dataframe_returns_none_for_unconvertible_value():
    assert dashboard._to_dataframe(5) is None


def test_zip_dir_keeps_relative_paths(tmp_path):
    source = tmp_path / "source"
    (source / "sub").mkdir(parents=True)
    (source / "a.txt").write_text("a")
    (source / "sub" / "b.txt").write_text("b")
    target = tmp_path / "out" / "archive.zip"

    dashboard._zip_dir(source, target)

    with zipfile.ZipFile(target) as archive:
        assert sorted(archive.namelist()) == ["a.txt", "sub/b.txt"]


def test_module_without_dash_sets_flag(monkeypatch):
    # A ``None`` entry makes ``import dash`` fail like a missing package.
    monkeypatch.setitem(sys.modules, "dash", None)
    spec = importlib.util.spec_from_file_location(
        "dashboard_without_dash", dashboard.__file__
    )
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    assert module.PLOTLY_DASH is False


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def test_export_dashboard(results, example_fig, tmp_path):
    json_figure = example_fig.to_plotly_json()
    results["test_figure"] = json_figure
    table = pd.DataFrame({"name": ["A", "B", "C"], "value": [10, 20, 30]})
    results["dummy_table"] = table
    results.autoassign_keys()

    results.export_results_to_datapackage(tmp_path)

    figure_path = tmp_path / "dashboard" / "elements" / "test_figure.json"
    assert figure_path.exists()
    with figure_path.open(encoding="utf-8") as file:
        assert json.load(file) == json_figure

    table_path = tmp_path / "dashboard" / "elements" / "dummy_table.csv"
    assert table_path.exists()
    exported = pd.read_csv(table_path, index_col=[0])
    exported.index.name = None
    pd.testing.assert_frame_equal(exported, table)


def test_export_results_to_zip(results, tmp_path):
    results["fig"] = {"data": []}
    results.figure_keys.append("fig")
    zip_path = tmp_path / "dashboard_results.zip"

    results.export_results_to_datapackage(zip_path, zip=True)

    assert zipfile.is_zipfile(zip_path)
    with zipfile.ZipFile(zip_path, "r") as archive:
        names = archive.namelist()
    assert "datapackage.json" in names
    assert any(name.startswith("results/") for name in names)
    assert any(name.startswith("dashboard/") for name in names)


def test_export_skips_eesyplan_namespace(results, tmp_path):
    results["eesyplan"] = {"lcoe": 1.0}
    results.figure_keys.append("eesyplan")

    resources = _export_dashboard_resources(results, tmp_path)

    assert resources == []
    assert not (tmp_path / "dashboard/elements/eesyplan.json").exists()


def test_export_writes_empty_file_for_missing_value(results, tmp_path):
    results.figure_keys.append("ghost")

    resources = _export_dashboard_resources(results, tmp_path)

    path = tmp_path / "dashboard" / "elements" / "ghost.csv"
    assert path.exists()
    assert path.read_text() == ""
    assert resources == [
        {
            "name": "ghost",
            "path": "dashboard/elements/ghost.csv",
            "kind": "element",
            "format": "csv",
            "dialect": {"header": False},
        }
    ]


def test_export_numeric_objective_as_table(results, tmp_path):
    results._data["objective"] = 12.5
    results.table_keys.append("objective")

    resources = _export_dashboard_resources(results, tmp_path)

    path = tmp_path / "dashboard" / "elements" / "objective.csv"
    exported = pd.read_csv(path, index_col=0)
    assert exported["objective"].tolist() == [12.5]
    assert [resource["name"] for resource in resources] == ["objective"]


def test_export_non_numeric_objective_as_empty_file(results, tmp_path):
    results._data["objective"] = "not a number"
    results.table_keys.append("objective")

    resources = _export_dashboard_resources(results, tmp_path)

    path = tmp_path / "dashboard" / "elements" / "objective.csv"
    assert path.read_text() == ""
    assert resources == [
        {
            "name": "objective",
            "path": "dashboard/elements/objective.csv",
            "kind": "element",
            "format": "csv",
            "dialect": {"header": True, "headerRows": [0]},
        }
    ]


# ---------------------------------------------------------------------------
# import_dashboard_results
# ---------------------------------------------------------------------------


def test_import_dashboard_results_accepts_string_paths(monkeypatch):
    def fail(es):
        raise AssertionError("existing results must not be optimised again")

    monkeypatch.setattr(dashboard, "optimise", fail)

    imported = dashboard.import_dashboard_results(
        str(SCENARIO_JSON), str(RESULTS_PATH)
    )

    assert isinstance(imported, DashboardResults)
    assert imported.energy_system is not None


def test_import_dashboard_results_optimises_missing_results(
    monkeypatch, tmp_path
):
    results_path = tmp_path / "new_results"
    calls = {}

    def fake_optimise(es):
        calls["optimise"] = es
        return "solved"

    def fake_export_results(results, path, component_type_mapping):
        calls["export"] = (results, path, component_type_mapping)
        # Provide the files the import afterwards expects.
        shutil.copytree(RESULTS_PATH, path)

    monkeypatch.setattr(dashboard, "optimise", fake_optimise)
    monkeypatch.setattr(dashboard, "export_results", fake_export_results)

    imported = dashboard.import_dashboard_results(SCENARIO_JSON, results_path)

    assert isinstance(imported, DashboardResults)
    assert calls["optimise"] is imported.energy_system
    assert calls["export"] == (
        "solved",
        results_path,
        get_component_type_mapping_from_dp(SCENARIO_JSON),
    )


# ---------------------------------------------------------------------------
# prepare_dash_app
# ---------------------------------------------------------------------------


def test_prepare_dash_app(dash_results):
    app = prepare_dash_app(dash_results)

    assert isinstance(app, dash.Dash)

    slider = _find_component(app, "ts_slice_slider")
    dropdown = _find_component(app, "ts_slice_select")
    timeindex = dash_results.energy_system.timeindex
    assert isinstance(slider, dcc.Slider)
    assert isinstance(dropdown, dcc.Dropdown)
    assert isinstance(_find_component(app, "sankey"), dcc.Graph)
    assert isinstance(_find_component(app, "sankey_aggregated"), dcc.Graph)
    assert slider.min == 0
    assert slider.max == len(timeindex)
    assert dropdown.options == dict(enumerate(timeindex))

    assert "sankey" in dash_results.figure_keys
    assert "..sankey.figure.." in app.callback_map
    assert "ts_slice_select.value" in app.callback_map


def test_prepare_dash_app_creates_bus_graphs(dash_results):
    app = prepare_dash_app(dash_results)

    component_ids = [
        getattr(component, "id", None)
        for component in _iter_components(app.layout)
    ]
    buses = [
        node
        for node in dash_results.energy_system.nodes
        if isinstance(node, CarrierBus)
    ]
    assert buses
    for bus in buses:
        assert f"bus_{bus}-id" in component_ids


def test_prepare_dash_app_bus_graph_signs(dash_results, sankey_calls):
    es = dash_results.energy_system
    bus = next(node for node in es.nodes if isinstance(node, CarrierBus))
    others = [node for node in es.nodes if not isinstance(node, CarrierBus)]
    supplier, consumer = others[:2]
    dash_results._data["flow"] = pd.DataFrame(
        [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
        index=pd.date_range("2023-01-01", periods=2, freq="h"),
        columns=pd.MultiIndex.from_tuples(
            # The last flow does not touch the bus and is skipped.
            [(supplier, bus), (bus, consumer), (supplier, consumer)]
        ),
    )

    app = prepare_dash_app(dash_results)

    figure = _find_component(app, f"bus_{bus}-id").figure
    traces = {trace.name: list(trace.y) for trace in figure.data}
    # Flows into the bus are positive, flows out of the bus negative.
    assert traces == {
        str(supplier.label): [1.0, 4.0],
        str(consumer.label): [-2.0, -5.0],
    }
    assert figure.layout.title.text == f"{bus} bus node"


def test_prepare_dash_app_shows_tables_and_figures(dash_results, example_fig):
    dash_results["kpis"] = pd.DataFrame({"name": ["A", "B"], "value": [1, 2]})
    dash_results.table_keys.append("kpis")
    dash_results["extra_fig"] = example_fig.to_plotly_json()
    dash_results.figure_keys.append("extra_fig")

    app = prepare_dash_app(dash_results)

    tables = [
        component
        for component in _iter_components(app.layout)
        if isinstance(component, dash_table.DataTable)
    ]
    assert len(tables) == 1
    assert tables[0].data == [
        {"name": "A", "value": 1},
        {"name": "B", "value": 2},
    ]
    assert [column["id"] for column in tables[0].columns] == ["name", "value"]
    assert _find_component(app, "batch_figure_extra_fig-id") is not None
    assert _find_component(app, "batch_figure_capacities-id") is not None


def test_sankey_callback_uses_selected_time_step(dash_results, sankey_calls):
    app = prepare_dash_app(dash_results)
    update_figures = _callback_function(app, "..sankey.figure..")

    default = update_figures(None)
    selected = update_figures("3")

    # The first entry is the call that builds the initial layout.
    assert sankey_calls == [None, 0, 3]
    assert len(default) == 1
    assert isinstance(default[0], go.Figure)
    assert default[0].layout.title.text == "row 0"
    assert selected[0].layout.title.text == "row 3"


def test_slider_callback_passes_value_to_dropdown(dash_results, sankey_calls):
    app = prepare_dash_app(dash_results)

    change_ts_value = _callback_function(app, "ts_slice_select.value")

    assert change_ts_value(7) == 7


# ---------------------------------------------------------------------------
# Command line interface
# ---------------------------------------------------------------------------


class _StubResults:
    """Records what the CLI does with the imported results."""

    def __init__(self):
        self.import_args = None
        self.calls = []

    def import_dashboard_results(self, scenario_path, results_path):
        self.import_args = (scenario_path, results_path)
        return self

    def add_all_figures(self):
        self.calls.append("figures")

    def add_all_tables(self):
        self.calls.append("tables")

    def export_results_to_datapackage(self, path):
        self.calls.append(("export", path))


def _run_cli(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["dashboard", *map(str, args)])
    dashboard.cli()


class TestCli:
    """Tests for cli()."""

    @pytest.fixture(autouse=True)
    def _quiet_logging(self, monkeypatch):
        # The real function writes log files to the home directory.
        monkeypatch.setattr(dashboard, "define_logging", lambda: None)

    @pytest.fixture
    def stubbed(self, monkeypatch):
        stub = _StubResults()
        monkeypatch.setattr(
            dashboard,
            "import_dashboard_results",
            stub.import_dashboard_results,
        )
        return stub

    def test_appends_datapackage_json_to_directories(
        self, stubbed, monkeypatch, tmp_path
    ):
        results_path = tmp_path / "results"

        _run_cli(monkeypatch, tmp_path, results_path, "-o", tmp_path / "out")

        assert stubbed.import_args == (
            tmp_path / "datapackage.json",
            results_path,
        )

    @pytest.mark.parametrize("suffix", [".json", ".zip"])
    def test_keeps_json_and_zip_scenarios(
        self, stubbed, monkeypatch, tmp_path, suffix
    ):
        scenario = tmp_path / f"scenario{suffix}"

        _run_cli(
            monkeypatch,
            scenario,
            tmp_path / "results",
            "-o",
            tmp_path / "out",
        )

        assert stubbed.import_args[0] == scenario

    def test_exports_instead_of_starting_app(
        self, stubbed, monkeypatch, tmp_path
    ):
        output = tmp_path / "out"
        monkeypatch.setattr(
            dashboard,
            "prepare_dash_app",
            lambda results: pytest.fail("no app expected"),
        )

        _run_cli(
            monkeypatch,
            tmp_path / "scenario.json",
            tmp_path / "results",
            "-o",
            output,
        )

        assert stubbed.calls == ["figures", "tables", ("export", output)]

    def test_logs_error_without_dash(
        self, stubbed, monkeypatch, tmp_path, caplog
    ):
        monkeypatch.setattr(dashboard, "PLOTLY_DASH", False)
        monkeypatch.setattr(
            dashboard,
            "prepare_dash_app",
            lambda results: pytest.fail("no app expected"),
        )

        with caplog.at_level(logging.ERROR):
            _run_cli(
                monkeypatch, tmp_path / "scenario.json", tmp_path / "results"
            )

        assert "Plotly dash is not installed" in caplog.text
        assert stubbed.calls == ["figures", "tables"]

    def test_end_to_end_starts_app(self, monkeypatch):
        calls = {"prepare": False, "run": False}

        class DummyApp:
            def run(self, debug=False, port=None):
                calls["run"] = True
                assert debug is True
                assert port == 8060

        def mock_prepare_dash_app(results):
            calls["prepare"] = True
            return DummyApp()

        monkeypatch.setattr(
            dashboard, "prepare_dash_app", mock_prepare_dash_app
        )

        _run_cli(monkeypatch, SCENARIO_PATH, RESULTS_PATH)

        assert calls["prepare"]
        assert calls["run"]


def test_module_runs_cli_when_executed_as_script(monkeypatch, capsys):
    monkeypatch.setattr(
        "oemof.tools.logger.define_logging", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(sys, "argv", ["dashboard", "--help"])

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(dashboard.__file__, run_name="__main__")

    assert excinfo.value.code == 0
    assert "scenario_path" in capsys.readouterr().out
