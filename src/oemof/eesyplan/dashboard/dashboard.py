import json
import tempfile
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

import dash
import pandas as pd
import plotly.graph_objs as go
from dash import dash_table
from dash import dcc
from dash import html
from dash.dependencies import Input
from dash.dependencies import Output

import oemof.eesyplan.postprocessing.graphs as graphs
from oemof.datapackage.resultpackage.read import ImportResults
from oemof.eesyplan import CarrierBus
from oemof.eesyplan import export_results
from oemof.eesyplan import import_results
from oemof.eesyplan.dashboard.graphs_to_json import sankey_to_json
from oemof.eesyplan.datapackage.energy_system import (
    create_energy_system_from_dp,
)
from oemof.eesyplan.model import optimise


def _normalize_df_for_csv(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """
    - Setzt einen Indexnamen, falls keiner existiert (für sauberere CSVs).
    - Normalisiert 'variable_costs' auf einen MultiIndex (from, to),

      wenn die Spalten Tupel sind.
    """
    df = df.copy()

    if df.index.name is None:
        df.index.name = "index"

    if key == "variable_costs":
        # Bug-Workaround: Spalten als Tupel -> zu MultiIndex(from, to)
        if not isinstance(df.columns, pd.MultiIndex):
            if all(isinstance(c, tuple) and len(c) == 2 for c in df.columns):
                df.columns = pd.MultiIndex.from_tuples(
                    df.columns, names=["from", "to"]
                )

    return df


def _export_df_resource(
    df: pd.DataFrame,
    key: str,
    results_root: Path,
    resources: list[dict[str, Any]],
) -> None:
    """
    Schreibt einen DataFrame als CSV nach
    - results/sequences/<key>.csv  (falls DatetimeIndex)
    - results/elements/<key>.csv   (sonst)

    und trägt die Ressource in 'resources' ein.
    """
    df = _normalize_df_for_csv(df, key)

    if isinstance(df.index, pd.DatetimeIndex):
        subdir = results_root / "sequences"
        kind = "sequence"
        rel_prefix = "results/sequences"
    else:
        subdir = results_root / "elements"
        kind = "element"
        rel_prefix = "results/elements"

    subdir.mkdir(parents=True, exist_ok=True)

    fname = f"{key}.csv"
    fpath = subdir / fname

    # MultiIndex-Spalten bleiben unverändert -> mehrere Headerzeilen im CSV
    df.to_csv(fpath)

    if isinstance(df.columns, pd.MultiIndex):
        header_rows = list(range(df.columns.nlevels))
    else:
        header_rows = [0]

    resources.append(
        {
            "name": key,
            "path": f"{rel_prefix}/{fname}",
            "kind": kind,
            "format": "csv",
            "dialect": {
                "header": True,
                "headerRows": header_rows,
            },
        }
    )


def _to_dataframe(value: Any) -> pd.DataFrame | None:
    """Versucht, einen Wert generisch in einen DataFrame zu wandeln."""
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if isinstance(value, pd.Series):
        return value.to_frame()
    try:
        return pd.DataFrame(value)
    except Exception:
        return None


def _zip_dir(src_dir: Path, zip_path: Path) -> None:
    """Packt den Inhalt von src_dir als ZIP nach zip_path."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zf:
        for file_path in src_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(src_dir)
                zf.write(file_path, arcname)


class DashboardResults(ImportResults):
    """
    Extend :class:`ImportResults` with dashboard-specific results and export
    functionality.

    ``DashboardResults`` wraps an existing ``ImportResults`` instance and
    preserves its internal state. Additional result objects, such as Plotly
    figures or tables, can then be added without overwriting the original
    result entries.

    The class distinguishes between core result keys inherited from
    ``ImportResults`` and additional dashboard keys. Core keys are protected
    against overwriting, while additional keys may be added dynamically.

    Parameters
    ----------
    imported_results : oemof.datapackage.ImportResults
        Existing imported results whose internal state is used to initialize
        this object.

    Attributes
    ----------
    figure_keys : list[str]
        Keys identifying dashboard entries containing Plotly figures.
    table_keys : list[str]
        Keys identifying dashboard entries containing tabular results.

    Notes
    -----
    Additional dashboard entries such as Plotly figures should be stored
    in a JSON-compatible representation, while tables are expected to
    be pandas ``DataFrame``objects.

    Here is an example of how to add figures/tables to the dashboard manually,
    the keys must also be registered in ``figure_keys``:

        imported_results = DashboardResults(...)
        imported_results["my_fonction"] = some_figure_fonction(imported_results)
        imported_results.figure_keys.append("my_fonction")

    Registered figure/table keys are used to identify which additional results
    should be treated and exported as dashboard figures/tables.
    """

    def __init__(self, imported_results, energy_system=None):
        self.__dict__.update(imported_results.__dict__)
        self.energy_system = energy_system
        self._core_keys = set(self.keys())
        self.figure_keys = []
        self.table_keys = []

    def __setitem__(self, key: str, value):
        if key not in self._data:
            if isinstance(value, pd.DataFrame) or isinstance(value, dict):
                self._data[key] = value
            else:
                raise TypeError(
                    f"The value you would like to assign to the DashboardResults instance under the key {key} is not a dataframe or a dict"
                )
        else:
            if key in self._core_keys:
                raise KeyError(
                    f"Key '{key}' already exists and is not overwritable"
                )

    def get(self, key, default=None):
        return self._data.get(key, default)

    def autoassign_keys(self):
        for key in self.keys():
            if key not in self._core_keys:
                if isinstance(self[key], dict) and key not in self.figure_keys:
                    self.figure_keys.append(key)
                if (
                    isinstance(self[key], pd.DataFrame)
                    and key not in self.table_keys
                ):
                    self.table_keys.append(key)

    def add_capacities_graph(self):
        fig = graphs.capacities_graph(self["invest"], self.energy_system)
        key = "capacities"
        self[key] = json.loads(fig.to_json())
        self.figure_keys.append(key)
        return key

    def figures(self, fig_keys=None):
        if fig_keys is None:
            fig_keys = self.figure_keys
        else:
            fig_keys = [k for k in fig_keys if k in self.keys()]

        figs = {}
        for k in fig_keys:
            figs[k] = self[k]

        return figs

    def tables(self, table_keys=None):
        if table_keys is None:
            table_keys = self.table_keys
        else:
            table_keys = [k for k in table_keys if k in self.keys()]

        tables = {}
        for k in table_keys:
            tables[k] = self[k]

        return tables

    def export_results_to_datapackage(
        self,
        base_path: str | Path,
        zip: bool = False,
    ) -> None:
        base_path = Path(base_path)

        if zip:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_root = Path(tmpdir)
                self._export_results_to_dir(tmp_root)
                self._export_results_to_dir(tmp_root, dashboard=True)
                _zip_dir(tmp_root, base_path)
        else:
            base_path.mkdir(parents=True, exist_ok=True)
            self._export_results_to_dir(base_path)
            self._export_results_to_dir(base_path, dashboard=True)

    def _export_results_to_dir(self, base_path: Path, dashboard=False) -> None:
        if dashboard:
            dp_folder = "dashboard"
            keys = self.figure_keys + self.table_keys
        else:
            dp_folder = "results"
            keys = self.keys()

        results_root = base_path / dp_folder

        (results_root / "elements").mkdir(
            parents=True,
            exist_ok=True,
        )
        (results_root / "sequences").mkdir(
            parents=True,
            exist_ok=True,
        )

        resources = []

        for key in keys:
            value = self.get(key)

            # here one should consider dict (figures), None (with warning) and DataFrame (tables)

            if isinstance(value, dict):
                fname = f"{key}.json"
                fpath = results_root / "elements" / fname
                fpath.touch()

                resources.append(
                    {
                        "name": key,
                        "path": f"{dp_folder}/elements/{fname}",
                        "kind": "element",
                        "format": "json",
                    }
                )
                f_path = results_root / "elements" / fname
                with f_path.open(
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(
                        value,
                        f,
                        indent=4,
                    )

            if value is None:
                fname = f"{key}.csv"
                fpath = results_root / "elements" / fname
                fpath.touch()

                resources.append(
                    {
                        "name": key,
                        "path": f"{dp_folder}/elements/{fname}",
                        "kind": "element",
                        "format": "csv",
                        "dialect": {
                            "header": False,
                        },
                    }
                )
                continue

            if key == "objective":
                try:
                    val = float(value)
                    df = pd.DataFrame({"objective": [val]})
                except Exception:
                    fname = "objective.csv"
                    fpath = results_root / "elements" / fname
                    fpath.touch()

                    resources.append(
                        {
                            "name": "objective",
                            "path": f"{dp_folder}/elements/objective.csv",
                            "kind": "element",
                            "format": "csv",
                            "dialect": {
                                "header": True,
                                "headerRows": [0],
                            },
                        }
                    )
                    continue

                _export_df_resource(
                    df,
                    "objective",
                    results_root,
                    resources,
                )
                continue

            if isinstance(value, pd.DataFrame):
                df = _to_dataframe(value)

                _export_df_resource(
                    df,
                    key,
                    results_root,
                    resources,
                )

        # here one should not erase existing datapackage, rather add things
        datapackage = {
            "name": "oemof_solph_results",
            "profile": "tabular-data-package",
            "resources": resources,
        }

        datapackage_path = base_path / "datapackage.json"
        with datapackage_path.open(
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                datapackage,
                f,
                indent=2,
            )


def import_dashboard_results(scenario_path, results_path):
    if isinstance(scenario_path, str):
        scenario_path = Path(scenario_path)
    if isinstance(results_path, str):
        results_path = Path(results_path)

    es = create_energy_system_from_dp(scenario_path)

    if not results_path.exists():
        results = optimise(es)
        export_results(results=results, path=results_path)

    imported_results = import_results(results_path, es)
    imported_results = DashboardResults(imported_results, es)
    return imported_results


def prepare_dash_app(imported_results):
    es = imported_results.energy_system
    flows = imported_results["flow"]

    bus_figures = []

    busses = [n for n in es.nodes if isinstance(n, CarrierBus)]
    for bus in busses:
        fig = go.Figure(layout={"title": f"{bus} bus node"})
        for col in flows.columns:
            if bus in col:
                idx_asset = abs(col.index(bus) - 1)
                fig.add_trace(
                    go.Scatter(
                        x=flows[col].index,
                        y=flows[col].values * pow(-1, idx_asset),
                        name=str(
                            col[idx_asset].label
                            if hasattr(col[idx_asset], "label")
                            else col[idx_asset]
                        ),
                    )
                )

        bus_figures.append(fig)

    # Here define which figures should be displayed
    capacity_fig_key = imported_results.add_capacities_graph()

    imported_results["sankey"] = sankey_to_json(imported_results)
    imported_results.figure_keys.append("sankey")

    figures_to_plot = [capacity_fig_key]

    # Here define which tables should be displayed
    # imported_results["yearly_project_costs"] = yearly_project_costs(
    #     imported_results, es
    # )
    # imported_results.table_keys.append("yearly_project_costs")
    #
    # imported_results["project_cost_table"] = project_cost_table(
    #     imported_results, es
    # )
    # imported_results.table_keys.append("project_cost_table")

    date_time_index = es.timeindex

    options = {}
    demo_app = dash.Dash(__name__, **options)

    demo_app.layout = html.Div(
        children=[html.H2("Scalar results"), html.H3("KPIS")]
        + [
            html.Div(
                [
                    html.H4(table),
                    dash_table.DataTable(
                        data=df.to_dict("records"),
                        columns=[
                            {"name": col, "id": col} for col in df.columns
                        ],
                    ),
                ]
            )
            for table, df in imported_results.tables().items()
        ]
        + [
            html.H2("Dynamic results"),
            dcc.Slider(
                id="ts_slice_slider",
                value=1,
                min=0,
                max=len(date_time_index),
                # marks={k: v for k, v in enumerate(date_time_index)},
            ),
            dcc.Dropdown(
                id="ts_slice_select",
                options=dict(enumerate(date_time_index)),
                value=None,
            ),
            dcc.Graph(id="sankey", figure=imported_results["sankey"]),
            html.H2("Graphs"),
            html.H4("Aggregated sankey diagramm"),
            dcc.Graph(
                id="sankey_aggregated", figure=imported_results["sankey"]
            ),
        ]
        + [
            html.Div(
                [
                    html.H4(fig_num),
                    dcc.Graph(
                        id=f"batch_figure_{fig_num}-id",
                        figure=fig,
                    ),
                ]
            )
            for fig_num, fig in imported_results.figures(
                figures_to_plot
            ).items()
        ]
        + [
            html.H2("Bus results"),
        ]
        + [
            dcc.Graph(
                id=f"bus_{bus}-id",
                figure=fig,
            )
            for bus, fig in zip(busses, bus_figures, strict=False)
        ]
    )

    @demo_app.callback(
        # The value of these components of the layout will be changed by this callback
        [
            Output(component_id="sankey", component_property="figure"),
        ],
        # Triggers the callback when the value of one of these components of the layout is changed
        Input(component_id="ts_slice_select", component_property="value"),
    )
    def update_figures(ts):
        if ts is None:
            ts = "0"
        ts = int(ts)

        sankey_fig = sankey_to_json(imported_results, row=ts)
        sankey_diagram = go.Figure(sankey_fig)

        return [
            sankey_diagram,
        ]

    @demo_app.callback(
        # The value of these components of the layout will be changed by this callback
        Output(component_id="ts_slice_select", component_property="value"),
        # Triggers the callback when the value of one of these components of the layout is changed
        Input(component_id="ts_slice_slider", component_property="value"),
    )
    def change_ts_value(val):
        return val

    return demo_app


