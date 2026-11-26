import json
import warnings
from unittest.mock import MagicMock
from unittest.mock import patch

import numpy as np
import pandas as pd

from oemof.datapackage import datapackage  # noqa
from oemof.eesyplan.datapackage import results as res_mod
from oemof.tools.debugging import ExperimentalFeatureWarning

warnings.filterwarnings("ignore", category=ExperimentalFeatureWarning)

MODULE = "oemof.eesyplan.datapackage.results"
WRITE = f"{MODULE}.write.export_results_to_datapackage"
PACKAGE = f"{MODULE}.Package"
TIMEINDEX = pd.date_range("2023-01-01", periods=5, freq="h")


def _results_mock(flows=None, flow_objects=None):
    """Dict-like results stand-in with a 5-step time index."""
    results = MagicMock()
    results.keys.return_value = []
    results._model.es.timeindex = TIMEINDEX
    if flows is None:
        results.__getitem__.side_effect = KeyError("flow")
    else:
        results.__getitem__.return_value = flows
        results._model.flows = flow_objects
    return results


@patch(WRITE)
def test_export_results_accepts_str_path(mock_write, tmp_path):
    # Fails without the fix Path(str) -> Path(path) (line 26)
    res_mod.export_results(_results_mock(), str(tmp_path))
    assert mock_write.call_args.kwargs["base_path"] == tmp_path


@patch(PACKAGE)
@patch(WRITE)
def test_export_results_without_flows_returns_empty_frame(
    mock_write, mock_package, tmp_path
):
    (tmp_path / "results").mkdir()
    mapping = {"wind": "WindTurbine"}

    out = res_mod.export_results(_results_mock(), tmp_path, mapping)

    assert isinstance(out, pd.DataFrame)
    assert out.empty
    written = tmp_path / "results" / "component_type_mapping.json"
    assert json.loads(written.read_text(encoding="utf-8")) == mapping
    mock_package.return_value.save.assert_not_called()


@patch.object(pd.DataFrame, "to_csv", autospec=True)
@patch(PACKAGE)
@patch(WRITE)
def test_export_results_variable_costs_array_and_scalar(
    mock_write, mock_package, mock_to_csv, tmp_path
):
    (tmp_path / "results").mkdir()
    flows = pd.DataFrame(
        np.ones((4, 2)),
        index=TIMEINDEX[:-1],
        columns=pd.MultiIndex.from_tuples([("a", "b"), ("b", "c")]),
    )
    flow_objects = {
        ("a", "b"): MagicMock(variable_costs=np.array([1.0, 2.0, 3.0, 4.0])),
        ("b", "c"): MagicMock(variable_costs=2.0),
    }
    package = mock_package.return_value
    package.get_resource.return_value.descriptor = {
        "path": "results/variable_costs.csv"
    }

    res_mod.export_results(
        _results_mock(flows, flow_objects), tmp_path, {"a": "X"}
    )

    df_opex = mock_to_csv.call_args.args[0]
    assert df_opex[("a", "b")].tolist() == [1.0, 2.0, 3.0, 4.0]
    assert df_opex[("b", "c")].tolist() == [2.0] * 4
    package.save.assert_called_once()
