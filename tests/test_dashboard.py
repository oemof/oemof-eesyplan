import json
import zipfile
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pytest

from oemof.eesyplan import import_results
from oemof.eesyplan.dashboard import DashboardResults
from oemof.eesyplan.datapackage.energy_system import (
    create_energy_system_from_dp,
)


@pytest.fixture
def energy_system():
    path = Path(Path(__file__).parent, "test_data", "openPlan_package")

    es = create_energy_system_from_dp(path)
    return es


@pytest.fixture
def imported_results(energy_system):
    # path = Path(Path(__file__).parent, "test_data", "openPlan_package")
    result_path = Path(
        Path(__file__).parent, "test_data", "openPlan_results_package"
    )
    imported_results = import_results(path=result_path, es=energy_system)

    return imported_results


@pytest.fixture
def example_fig():
    fig = go.Figure(
        data=[
            go.Scatter(
                x=[1, 2, 3],
                y=[4, 5, 6],
                mode="lines",
            )
        ]
    )
    return fig


def test_dashboard_results_initialization(imported_results, energy_system):
    results = DashboardResults(imported_results, energy_system)

    assert results.energy_system is energy_system
    assert results._core_keys == set(imported_results.keys())
    assert results.figure_keys == []
    assert results.table_keys == []


def test_add_extra_key(imported_results, energy_system):
    results = DashboardResults(imported_results, energy_system)

    results["my_figure"] = {
        "data": [],
        "layout": {},
    }

    assert "my_figure" in results.keys()
    assert results["my_figure"] == {
        "data": [],
        "layout": {},
    }


def test_core_key_cannot_be_overwritten(imported_results, energy_system):
    results = DashboardResults(imported_results, energy_system)

    core_key = next(iter(results._core_keys))

    with pytest.raises(
        KeyError,
        match="already exists and is not overwritable",
    ):
        results[core_key] = {}


def test_figures(imported_results, energy_system):
    results = DashboardResults(imported_results, energy_system)

    fig_1 = {
        "data": [{"x": [1, 2]}],
    }
    fig_2 = {
        "data": [{"x": [3, 4]}],
    }

    results["fig_1"] = fig_1
    results["fig_2"] = fig_2

    results.figure_keys.extend(["fig_1", "fig_2"])

    assert results.figures() == {
        "fig_1": fig_1,
        "fig_2": fig_2,
    }

    assert results.figures(["fig_1"]) == {
        "fig_1": fig_1,
    }


def test_figures_ignores_unknown_keys(imported_results, energy_system):
    results = DashboardResults(imported_results, energy_system)

    results["fig_1"] = {
        "data": [],
    }
    results.figure_keys.append("fig_1")

    assert results.figures(["fig_1", "does_not_exist"]) == {
        "fig_1": {
            "data": [],
        },
    }


def test_export_dashboard(
    imported_results,
    energy_system,
    example_fig,
    tmp_path,
):
    results = DashboardResults(imported_results, energy_system)

    json_figure = example_fig.to_plotly_json()
    results["test_figure"] = json_figure

    df = pd.DataFrame(
        {
            "name": ["A", "B", "C"],
            "value": [10, 20, 30],
        }
    )
    results["dummy_table"] = df

    results.autoassign_keys()

    results.export_results_to_datapackage(tmp_path)

    figure_path = tmp_path / "dashboard" / "elements" / "test_figure.json"

    assert figure_path.exists()

    with figure_path.open(encoding="utf-8") as f:
        exported_figure = json.load(f)

    assert exported_figure == json_figure

    table_path = tmp_path / "dashboard" / "elements" / "dummy_table.csv"

    assert table_path.exists()

    exported_df = pd.read_csv(table_path, index_col=[0])
    exported_df.index.name = None

    pd.testing.assert_frame_equal(
        exported_df,
        df,
    )


def test_get_existing_key(imported_results, energy_system):
    results = DashboardResults(imported_results, energy_system)

    results["extra"] = {"adict": 123}

    assert results.get("extra") == {"adict": 123}


def test_get_missing_key_returns_default(
    imported_results,
    energy_system,
):
    results = DashboardResults(imported_results, energy_system)

    assert results.get("does_not_exist") is None
    assert results.get("does_not_exist", 42) == 42


def test_extra_key_is_not_core_key(imported_results, energy_system):
    results = DashboardResults(imported_results, energy_system)

    results["extra"] = {
        "some": "value",
    }

    assert "extra" in results.keys()
    assert "extra" not in results._core_keys


def test_figure_keys_only_contains_registered_figures(
    imported_results,
    energy_system,
):
    results = DashboardResults(imported_results, energy_system)

    results["fig"] = {
        "data": [],
    }
    results["other"] = {
        "foo": "bar",
    }

    results.figure_keys.append("fig")

    assert results.figures() == {
        "fig": {
            "data": [],
        },
    }


def test_assign_plotly_figure(imported_results, energy_system, example_fig):
    results = DashboardResults(imported_results, energy_system)

    fig_json = example_fig.to_plotly_json()

    results["plotly_fig"] = fig_json
    results.figure_keys.append("plotly_fig")

    assert "plotly_fig" in results.keys()
    assert "plotly_fig" in results.figure_keys

    stored_figure = results["plotly_fig"]

    assert isinstance(stored_figure, dict)
    assert "data" in stored_figure
    assert "layout" in stored_figure

    assert stored_figure["data"][0]["type"] == "scatter"
    assert list(stored_figure["data"][0]["x"]) == [1, 2, 3]
    assert list(stored_figure["data"][0]["y"]) == [4, 5, 6]


def test_export_results_to_zip(
    imported_results,
    energy_system,
    tmp_path,
):
    results = DashboardResults(imported_results, energy_system)

    results["fig"] = {
        "data": [],
    }

    results.figure_keys.append("fig")

    zip_path = tmp_path / "dashboard_results.zip"

    results.export_results_to_datapackage(
        zip_path,
        zip=True,
    )

    assert zip_path.exists()
    assert zipfile.is_zipfile(zip_path)

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()

    assert "datapackage.json" in names
    assert any(name.startswith("results/") for name in names)
    assert any(name.startswith("dashboard/") for name in names)
