import argparse
import importlib
import runpy
import shutil
import sys
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

ES_MODULE = "oemof.eesyplan.datapackage.energy_system"
DP_DIR = Path(Path(__file__).parent, "test_data", "openPlan_package")


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
    results_path = Path(
        Path(__file__).parent, "test_data", "openplan_results_test_package"
    )
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


def test_visio_import_fallback(monkeypatch):
    # Lines 20-21: oemof.visio cannot be imported
    try:
        with monkeypatch.context() as m:
            m.setitem(sys.modules, "oemof.visio", None)
            importlib.reload(es)
            assert es.ESGraphRenderer is None
    finally:
        importlib.reload(es)


def test_component_type_mapping_from_folder_and_json():
    from_folder = es.get_component_type_mapping_from_dp(DP_DIR)
    from_json = es.get_component_type_mapping_from_dp(
        DP_DIR / "datapackage.json"
    )
    assert from_folder
    assert from_folder == from_json
    assert all(isinstance(v, str) for v in from_folder.values())


def test_component_type_mapping_from_zip(tmp_path):
    archive = shutil.make_archive(str(tmp_path / "pkg"), "zip", DP_DIR)
    expected = es.get_component_type_mapping_from_dp(DP_DIR)
    assert es.get_component_type_mapping_from_dp(Path(archive)) == expected


def test_component_type_mapping_zip_with_two_json_files(tmp_path):
    archive = shutil.make_archive(str(tmp_path / "pkg"), "zip", DP_DIR)
    with zipfile.ZipFile(archive, "a") as zf:
        zf.write(
            Path(Path(__file__).parent, "test_data", "dp2.json"),
            arcname="dp2.json",
        )
    with pytest.raises(ValueError, match="To many json files"):
        es.get_component_type_mapping_from_dp(Path(archive))


def test_plot_es_renders_graph(tmp_path):
    with patch(f"{ES_MODULE}.ESGraphRenderer") as renderer:
        es.plot_es("my_es", tmp_path)
    renderer.assert_called_once_with(
        "my_es",
        legend=False,
        filepath=str(tmp_path / "energy_system_graph.png"),
        img_format="png",
    )
    renderer.return_value.render.assert_called_once_with()


@pytest.mark.parametrize(
    ("attributemap", "expected"),
    [(None, {}), ({"x": {"a": "b"}}, {"x": {"a": "b"}})],
)
@patch(f"{ES_MODULE}.optimise")
@patch(f"{ES_MODULE}.create_energy_system_from_dp")
def test_solve_passes_attributemap(
    mock_create, mock_optimise, attributemap, expected
):
    mock_optimise.return_value = "results"
    out = es.solve_energy_system_from_dp("x", attributemap=attributemap)
    mock_create.assert_called_once_with("x", attributemap=expected)
    mock_optimise.assert_called_once_with(mock_create.return_value)
    assert out == "results"


@pytest.mark.parametrize("as_str", [False, True])
@patch(f"{ES_MODULE}.get_component_type_mapping_from_dp", return_value={})
@patch(f"{ES_MODULE}.export_results")
@patch(f"{ES_MODULE}.optimise")
@patch(f"{ES_MODULE}.create_energy_system_from_dp")
def test_solve_exports_results(
    mock_create, mock_optimise, mock_export, mock_mapping, as_str, tmp_path
):
    target = tmp_path / "res"
    out = es.solve_energy_system_from_dp(
        "x", results_path=str(target) if as_str else target
    )
    assert out == target
    assert target.is_dir()
    mock_export.assert_called_once_with(
        mock_optimise.return_value, path=target, component_type_mapping={}
    )


def test_module_main_guard_runs_cli(monkeypatch):
    # Line 227: "--help" ends the CLI right after argument parsing
    monkeypatch.setattr(sys, "argv", ["solve datapackage", "--help"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        with pytest.raises(SystemExit) as excinfo:
            runpy.run_module(ES_MODULE, run_name="__main__")
    assert excinfo.value.code == 0
