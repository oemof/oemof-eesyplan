import argparse
import shutil
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from oemof.datapackage import datapackage  # noqa
from oemof.eesyplan import import_results
from oemof.eesyplan.datapackage import energy_system as es
from oemof.tools.debugging import ExperimentalFeatureWarning

warnings.filterwarnings("ignore", category=ExperimentalFeatureWarning)


@patch("oemof.eesyplan.datapackage.energy_system.solve_energy_system_from_dp")
@patch("oemof.eesyplan.datapackage.energy_system.argparse.ArgumentParser")
def test_cli_json_file(mock_parser, mock_solve):
    mock_parser.return_value.parse_args.return_value = argparse.Namespace(
        filename="some/datapackage.json",
        plot="graph",
        output=None,
    )
    es.cli()
    call_kwargs = mock_solve.call_args.kwargs
    assert call_kwargs["path"] == Path("some/datapackage.json")
    assert mock_solve.call_args.kwargs["plot"] == "graph"
    assert mock_solve.call_args.kwargs["results_path"] is None


@patch("oemof.eesyplan.datapackage.energy_system.solve_energy_system_from_dp")
@patch("oemof.eesyplan.datapackage.energy_system.argparse.ArgumentParser")
def test_cli_folder_path(mock_parser, mock_solve):
    mock_parser.return_value.parse_args.return_value = argparse.Namespace(
        filename="some/folder",
        plot="graph",
        output="out",
    )
    es.cli()
    assert mock_solve.call_args.kwargs["path"] == Path(
        "some", "folder", "datapackage.json"
    )
    assert mock_solve.call_args.kwargs["results_path"] == Path("out")


@patch("oemof.eesyplan.datapackage.energy_system.EnergySystem")
def test_create_es_from_folder(mock_es_class):
    mock_es_class.from_datapackage.return_value = "mock_es"
    path = Path("test_data/openPlan_package")
    result = es.create_energy_system_from_dp(path)
    assert result == "mock_es"
    # check it appended datapackage.json
    called_path = mock_es_class.from_datapackage.call_args.args[0]
    assert called_path.name == "datapackage.json"


@patch("oemof.eesyplan.datapackage.energy_system.optimise")
@patch("oemof.eesyplan.datapackage.energy_system.plot_es")
@patch("oemof.eesyplan.datapackage.energy_system.create_energy_system_from_dp")
def test_solve_with_visio_plot(mock_create, mock_plot, mock_optimise):
    mock_create.return_value = None
    es.solve_energy_system_from_dp("x", plot="visio")
    mock_plot.assert_called_once()


def test_simple_datapackage():
    path = Path(Path(__file__).parent, "test_data", "openPlan_package")
    results_path = Path(Path.home(), "openplan")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        result_path = es.solve_energy_system_from_dp(
            path, plot="graph", results_path=results_path
        )

    assert Path(path.parent, "openPlan_package.graphml").exists()
    Path(path.parent, "openPlan_package.graphml").unlink()
    import_results(path=result_path, es=es.create_energy_system_from_dp(path))
    shutil.rmtree(result_path)
    assert not result_path.exists()


@patch("oemof.eesyplan.datapackage.energy_system.ESGraphRenderer", None)
def test_visio_not_installed_trigger_helpful_error_message():
    dir_name = Path(Path(__file__).parent, "test_data", "openPlan_package")
    dummy_es = None
    with pytest.raises(
        ModuleNotFoundError,
        match="To use the plot function 'oemof-viso' must be installed",
    ):
        es.plot_es(dummy_es, dir_name)


def test_zip_datapackage():
    dir_name = Path(Path(__file__).parent, "test_data", "openPlan_package")
    filename = Path(Path(__file__).parent, "test_data", "openPlan_package")
    shutil.make_archive(str(filename), "zip", dir_name)
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=FutureWarning)
        result_path = Path(Path.home(), ".oemof", "test_eesyplan_567263FG")
        es.solve_energy_system_from_dp(filename, results_path=result_path)
        es.solve_energy_system_from_dp(
            filename.with_suffix(".zip"), plot="graph"
        )
        mzip = zipfile.ZipFile(filename.with_suffix(".zip"), "a")
        mzip.write(Path(Path(__file__).parent, "test_data", "dp2.json"))
        mzip.close()
    with pytest.raises(ValueError, match="To many json files"):
        es.solve_energy_system_from_dp(filename.with_suffix(".zip"))
    Path(dir_name.parent, "openPlan_package.graphml").unlink()
    filename.with_suffix(".zip").unlink()
