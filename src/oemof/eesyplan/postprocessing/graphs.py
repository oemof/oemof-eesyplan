import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative

from oemof.eesyplan import CarrierBus
from oemof.eesyplan import EnergySystem
from oemof.eesyplan import Shortage
from oemof.eesyplan.postprocessing.KPIs import _column_parts
from oemof.eesyplan.postprocessing.KPIs import _eesyplan_kpis
from oemof.eesyplan.postprocessing.KPIs import _owner_map
from oemof.eesyplan.postprocessing.KPIs import _owner_of_parts
from oemof.eesyplan.postprocessing.KPIs import _renewable_fraction
from oemof.eesyplan.postprocessing.KPIs import clean_label
from oemof.eesyplan.postprocessing.KPIs import yearly_project_costs
from oemof.solph.components import Source

_COMPONENT_TYPE_ORDER = [
    "buses",
    "compansation",
    "compensation",
    "converters",
    "demand",
    "production",
    "providers",
    "storages",
    "transport",
]

_COMPONENT_TYPE_COLORS = [
    "#7f7f7f",  # buses
    "#8c564b",  # compansation
    "#8c564b",  # compensation
    "#ff7f0e",  # converters
    "#d62728",  # demand
    "#2ca02c",  # production
    "#9467bd",  # providers
    "#1f77b4",  # storages
    "#17becf",  # transport
]

_COST_COLUMNS = [
    "annualized investment cost",
    "fix operational costs",
    "dispatch costs",
]

_COST_PATTERNS = ["", "x", "/"]


def _format_number(value, decimals=1):
    """Format a number with space as thousands separator."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    try:
        return f"{float(value):,.{decimals}f}".replace(",", " ")
    except Exception:
        return str(value)


def _cost_type_marker(color, pattern):
    """Marker of one cost type: the colour with its fill pattern."""
    marker = {"color": color}
    if pattern:
        marker["pattern"] = {
            "shape": pattern,
            "fgcolor": color,
            "bgcolor": "rgba(0,0,0,0)",
        }
    return marker


def _label_of(part):
    """Return the component label of one results column element."""
    label = getattr(part, "label", None)
    if label is not None:
        return str(label)
    text = str(part)
    match = re.search(r":\s*'([^']*)'", text)
    if match is None:
        match = re.search(r"<\w+\s+'([^']*)'", text)
    if match:
        return match.group(1)
    return text


def _rgba(color, alpha):
    """Return ``color`` as an rgba string with the given opacity."""
    red, green, blue = (
        int(color.lstrip("#")[index : index + 2], 16) for index in (0, 2, 4)
    )
    return f"rgba({red}, {green}, {blue}, {alpha})"


_COMPENSATION_COMPONENTS = {"excess", "shortage"}


def _facade_label(part):
    """Return the label without an internal component prefix.

    Internal components carry tuple labels such as
    ``("consumption_converter", "Gasversorger")``.  Only the facade part
    is relevant for the legend.  Compensation components such as
    ``("excess", "Strom_bus")`` keep their local name, because they are
    separate nodes and must not be folded into the bus.
    """
    label = _raw_label(part)
    if isinstance(label, tuple):
        return _facade_of(part)

    text = clean_label(part)
    local_name = text.split(" | ", 1)[0]
    if local_name in _COMPENSATION_COMPONENTS:
        return f"{text.rsplit(' | ', 1)[-1]} ({local_name})"
    return text.rsplit(" | ", 1)[-1]


def _raw_label(part):
    """Return the raw label of a node, internal components keep their tuple."""
    return getattr(part, "label", part)


def _facade_of(part):
    """Return the facade of a node, internal components are folded in.

    A node of a facade carries a tuple label such as
    ``("internal_bus", "Gasversorger")``.  For the diagram only the
    facade itself is of interest.  Compensation components such as
    ``("excess", "Strom_bus")`` are kept as separate nodes and therefore
    retain their local name.
    """
    label = _raw_label(part)
    if isinstance(label, tuple):
        local_name = str(label[0])
        facade = str(label[-1])
        if local_name in _COMPENSATION_COMPONENTS:
            return f"{facade} ({local_name})"
        return facade
    return str(label)


def _component_type_index(node):
    """Return index of component type based on components folder order."""
    if node is None:
        return None
    module = getattr(type(node), "__module__", "") or ""
    if ".components." not in module:
        return None
    try:
        subpath = module.split(".components.", 1)[1]
        type_name = subpath.split(".", 1)[0]
    except Exception:
        return None
    if type_name in _COMPONENT_TYPE_ORDER:
        return _COMPONENT_TYPE_ORDER.index(type_name)
    return None


def _node_type_color(node):
    idx = _component_type_index(node)
    if idx is None:
        return None
    return _COMPONENT_TYPE_COLORS[idx % len(_COMPONENT_TYPE_COLORS)]


def sankey(
    flows: pd.DataFrame,
    es: EnergySystem = None,
    title: str = "Sankey Diagram",
    row: int | str | pd.Timestamp | None = None,
    agg: str = "sum",
    drop_zero_links: bool = False,
) -> tuple[go.Figure, pd.DataFrame]:
    """
    Create a Plotly Sankey diagram from a DataFrame whose columns are a
    2-level MultiIndex: columns = MultiIndex[(source, target), ...]

    Parameters
    ----------
    es : EnergySystem
        Energy system object from eesyplan.EnergySystem.
    flows : pd.DataFrame
        Result.get("flow") of an oemof.solph Result object
    title : str
        Figure title.
    row : int | str | pd.Timestamp | None
        If None, aggregate across rows using `agg`.
        If provided, use only that row (by integer position or index label).
    agg : str
        Aggregation across rows when row is None. One of: "sum", "mean", "max".
    drop_zero_links : bool
        Whether to remove links with value == 0.

    Returns
    -------
    fig : go.Figure
        Plotly Sankey figure.
    links_df : pd.DataFrame
        Parsed links table with columns: source, target, value.
    """
    if not isinstance(flows.columns, pd.MultiIndex):
        raise TypeError("flows.columns must be a pandas MultiIndex.")

    if flows.columns.nlevels != 2:
        raise ValueError(
            "This function expects exactly 2 column levels: (source, target)."
        )

    if flows.empty:
        raise ValueError("Input DataFrame is empty.")

    numeric_df = flows

    # Statistics over the full time series
    ts_min = numeric_df.min(axis=0)
    ts_max = numeric_df.max(axis=0)

    if agg == "sum":
        ts_agg = numeric_df.sum(axis=0)
    elif agg == "mean":
        ts_agg = numeric_df.mean(axis=0)
    elif agg == "max":
        ts_agg = numeric_df.max(axis=0)
    else:
        raise ValueError("agg must be one of: 'sum', 'mean', or 'max'")

    selected_label = None

    # Value actually plotted
    if row is None:
        plotted_values = ts_agg.copy()
    else:
        if isinstance(row, int):
            plotted_values = flows.iloc[row]
            selected_label = flows.index[row]
        else:
            plotted_values = flows.loc[row]
            selected_label = row

    # Build link table
    links_df = pd.DataFrame(
        {
            "source": [str(src) for src, tgt in plotted_values.index],
            "target": [str(tgt) for src, tgt in plotted_values.index],
            "value": plotted_values.values,
            "min": ts_min.values,
            "max": ts_max.values,
            "aggregate": ts_agg.values,
        }
    )

    if drop_zero_links:
        links_df = links_df[links_df["value"] != 0].copy()
    else:
        links_df["value"] = links_df["value"].replace(0, 1e-9)

    if links_df.empty:
        raise ValueError("No links remain after filtering.")

    # TODO here the nodes need to hide the level behind the atomic components
    #  (this should be done by filtering at the results level)
    # Build node mapping
    nodes = (
        pd.Index(links_df["source"])
        .append(pd.Index(links_df["target"]))
        .unique()
    )
    node_map = {node: i for i, node in enumerate(nodes)}

    if row is None:
        customdata = links_df[["min", "max", "aggregate"]].to_numpy()
        hovertemplate = (
            "Source: %{source.label}<br>"
            "Target: %{target.label}<br>"
            "Plotted value: %{value}<br>"
            "Min: %{customdata[0]}<br>"
            "Max: %{customdata[1]}<br>"
            "Aggregate: %{customdata[2]}"
            "<extra></extra>"
        )
    else:
        links_df["timestamp"] = str(selected_label)
        customdata = links_df[
            ["min", "max", "aggregate", "timestamp"]
        ].to_numpy()
        hovertemplate = (
            "Source: %{source.label}<br>"
            "Target: %{target.label}<br>"
            "Timestamp: %{customdata[3]}<br>"
            "Plotted value: %{value}<br>"
            "Min: %{customdata[0]}<br>"
            "Max: %{customdata[1]}<br>"
            "Aggregate: %{customdata[2]}"
            "<extra></extra>"
        )

    node_colors = None
    if es is not None:
        node_colors = []
        es_nodes = list(es.nodes)
        es_node_labels = [str(n.label) for n in es.nodes]
        for n in nodes:
            if n in es_node_labels:
                node_idx = es_node_labels.index(n)
                es_node = es_nodes[node_idx]
                if isinstance(es_node, CarrierBus):
                    color = "grey"
                else:
                    if len(es_node.inputs) == 0:
                        color = "blue"
                    elif len(es_node.outputs) == 0:
                        color = "red"
                    else:
                        color = "green"
                node_colors.append(color)

    fig = go.Figure(
        go.Sankey(
            node={
                "pad": 15,
                "thickness": 20,
                "line": {"color": "black", "width": 0.5},
                "label": nodes.tolist(),
                "color": node_colors,
            },
            link={
                "source": links_df["source"].map(node_map).tolist(),
                "target": links_df["target"].map(node_map).tolist(),
                "value": links_df["value"].tolist(),
                "customdata": customdata,
                "hovertemplate": hovertemplate,
            },
        )
    )

    fig.update_layout(title_text=title, font_size=12)
    return fig, links_df


def sankey_2(
    results,
    es: EnergySystem = None,
    title: str = "Sankey Diagram",
    row: int | str | pd.Timestamp | None = None,
    agg: str = "sum",
    drop_zero_links: bool = True,
    collapse_fascades: bool = True,
) -> tuple[go.Figure, pd.DataFrame]:
    """
    Create a Plotly Sankey diagram from an imported results object.

    This is a copy of :func:`sankey` that works on the results object
    instead of the flow DataFrame.  The flow DataFrame is taken from the
    ``"flow"`` key of the results.

    Parameters
    ----------
    results : ImportResults or pd.DataFrame
        Imported results object, whose ``"flow"`` entry is used, or the
        flow DataFrame itself.
    es : EnergySystem
        Energy system object from eesyplan.EnergySystem.
    title : str
        Figure title.
    row : int | str | pd.Timestamp | None
        If None, aggregate across rows using `agg`.
        If provided, use only that row (by integer position or index label).
    agg : str
        Aggregation across rows when row is None. One of: "sum", "mean", "max".
    drop_zero_links : bool
        Whether to remove links with value == 0.
    collapse_fascades : bool
        Whether the internal components of a facade (e.g. the internal
        bus and the converters of a DSO) are folded into the facade
        itself.  Links of the same facade are merged, links inside a
        facade are dropped.  Defaults to True.

    Returns
    -------
    fig : go.Figure
        Plotly Sankey figure.
    links_df : pd.DataFrame
        Parsed links table with columns: source, target, value, max,
        aggregate.
    """
    flows = results if isinstance(results, pd.DataFrame) else results["flow"]

    if not isinstance(flows.columns, pd.MultiIndex):
        raise TypeError("flows.columns must be a pandas MultiIndex.")

    if flows.columns.nlevels != 2:
        raise ValueError(
            "This function expects exactly 2 column levels: (source, target)."
        )

    if flows.empty:
        raise ValueError("Input DataFrame is empty.")

    numeric_df = flows

    # Statistics over the full time series
    ts_max = numeric_df.max(axis=0)

    if agg == "sum":
        ts_agg = numeric_df.sum(axis=0)
    elif agg == "mean":
        ts_agg = numeric_df.mean(axis=0)
    elif agg == "max":
        ts_agg = numeric_df.max(axis=0)
    else:
        raise ValueError("agg must be one of: 'sum', 'mean', or 'max'")

    selected_label = None

    # Value actually plotted
    if row is None:
        plotted_values = ts_agg.copy()
    else:
        if isinstance(row, int):
            plotted_values = flows.iloc[row]
            selected_label = flows.index[row]
        else:
            plotted_values = flows.loc[row]
            selected_label = row

    # Build link table
    if collapse_fascades:
        sources = [_facade_of(src) for src, _ in plotted_values.index]
        targets = [_facade_of(tgt) for _, tgt in plotted_values.index]
    else:
        sources = [str(src) for src, _ in plotted_values.index]
        targets = [str(tgt) for _, tgt in plotted_values.index]

    links_df = pd.DataFrame(
        {
            "source": sources,
            "target": targets,
            "value": plotted_values.values,
            "max": ts_max.values,
            "aggregate": ts_agg.values,
        }
    )

    if collapse_fascades:
        links_df = links_df.groupby(
            ["source", "target"], as_index=False, sort=False
        )[["value", "max", "aggregate"]].sum()
        links_df = links_df[links_df["source"] != links_df["target"]].copy()

    if drop_zero_links:
        links_df = links_df[links_df["value"] != 0].copy()
    else:
        links_df["value"] = links_df["value"].replace(0, 1e-9)

    if links_df.empty:
        raise ValueError("No links remain after filtering.")

    # Nodes are already collapsed to their facade when ``collapse_fascades``
    # is set, so no further hiding of internal components is needed here.
    # Build node mapping
    nodes = (
        pd.Index(links_df["source"])
        .append(pd.Index(links_df["target"]))
        .unique()
    )
    node_map = {node: i for i, node in enumerate(nodes)}

    if row is None:
        customdata = np.column_stack(
            [
                [
                    _format_number(v / 1000.0, 1)
                    for v in links_df["value"].to_numpy()
                ],
                [_format_number(v, 1) for v in links_df["max"].to_numpy()],
                [
                    _format_number(v / 1000.0, 1)
                    for v in links_df["aggregate"].to_numpy()
                ],
            ]
        )
        hovertemplate = (
            "Source: %{source.label}<br>"
            "Target: %{target.label}<br>"
            "Plotted value: %{customdata[0]} MWh<br>"
            "Max: %{customdata[1]} kW<br>"
            "Aggregate: %{customdata[2]} MWh"
            "<extra></extra>"
        )
    else:
        links_df["timestamp"] = str(selected_label)
        customdata = np.column_stack(
            [
                [
                    _format_number(v / 1000.0, 1)
                    for v in links_df["value"].to_numpy()
                ],
                [_format_number(v, 1) for v in links_df["max"].to_numpy()],
                [
                    _format_number(v / 1000.0, 1)
                    for v in links_df["aggregate"].to_numpy()
                ],
                links_df["timestamp"].to_numpy(),
            ]
        )
        hovertemplate = (
            "Source: %{source.label}<br>"
            "Target: %{target.label}<br>"
            "Timestamp: %{customdata[3]}<br>"
            "Max: %{customdata[1]} kW<br>"
            "Aggregate: %{customdata[2]} MWh"
            "<extra></extra>"
        )

    node_colors = None
    if es is not None:
        node_colors = []
        es_nodes = list(es.nodes)
        es_node_labels = [str(n.label) for n in es.nodes]
        es_facade_labels = [_facade_of(n) for n in es.nodes]
        for n in nodes:
            if n in es_node_labels:
                es_node = es_nodes[es_node_labels.index(n)]
            elif n in es_facade_labels:
                es_node = es_nodes[es_facade_labels.index(n)]
            else:
                es_node = None
            if es_node is None:
                node_colors.append(None)
            else:
                type_color = _node_type_color(es_node)
                if type_color is not None:
                    node_colors.append(type_color)
                elif isinstance(es_node, CarrierBus):
                    node_colors.append("grey")
                elif len(getattr(es_node, "inputs", [])) == 0:
                    node_colors.append("blue")
                elif len(getattr(es_node, "outputs", [])) == 0:
                    node_colors.append("red")
                else:
                    node_colors.append("green")

    fig = go.Figure(
        go.Sankey(
            node={
                "pad": 15,
                "thickness": 20,
                "line": {"color": "black", "width": 0.5},
                "label": nodes.tolist(),
                "color": node_colors,
                "align": "left",
            },
            link={
                "arrowlen": 15,
                "source": links_df["source"].map(node_map).tolist(),
                "target": links_df["target"].map(node_map).tolist(),
                "value": links_df["value"].tolist(),
                "customdata": customdata,
                "hovertemplate": hovertemplate,
            },
        )
    )

    fig.update_layout(title_text=title, font_size=12)
    return fig, links_df


def capacities_graph(
    invest: pd.DataFrame, energy_system: EnergySystem
) -> go.Figure:
    """
    Create a grouped bar chart comparing installed and optimized capacities
    for energy system components.

    The function extracts installed capacities from nodes in ``energy_system``
    that provide an ``installed_capacity`` attribute and matches them against
    optimized capacities from ``invest``.

    Parameters
    ----------
    invest : pandas.DataFrame
        Obtained from oemof.solph.Result object accessing the 'invest' key
    energy_system : oemof.eesyplan.model.EnergySystem

    Returns
    -------
    plotly.graph_objects.Figure
        Plotly figure containing a grouped bar chart with installed and
        optimized capacities for each component.
    """

    optimized_map = {}
    for column, value in invest.iloc[0].items():
        parts = column if isinstance(column, tuple) else (column,)
        for part in parts:
            label = _label_of(part)
            if label not in optimized_map or value > optimized_map[label]:
                optimized_map[label] = value

    components = []
    installed_capacities = []
    for n in energy_system.nodes:
        if hasattr(n, "installed_capacity"):
            components.append(n.label)
            installed_capacities.append(n.installed_capacity)

    df = pd.DataFrame(
        {"component": components, "installed_capacity": installed_capacities}
    )

    df["optimized_capacity"] = df["component"].map(optimized_map).fillna(0)

    fig = go.Figure()

    fig.add_bar(
        x=df["component"].astype(str),
        y=df["installed_capacity"],
        name="Installed capacity",
        marker={
            "color": "#d64e12",
            "pattern": {
                "shape": "x",
                "fgcolor": "#d64e12",
                "bgcolor": "rgba(0,0,0,0)",
            },
        },
    )

    fig.add_bar(
        x=df["component"].astype(str),
        y=df["optimized_capacity"],
        name="Optimized capacity",
        marker={"color": "#d64e12"},
    )

    fig.update_layout(
        barmode="stack",
        xaxis_title="Component",
        yaxis_title="Capacity",
        margin={"b": 150},
        title="Installed vs Optimized Capacity",
    )

    return fig


def capacities(imported_results, es, threshold=1e-6) -> go.Figure:
    """
    Create a bar chart of installed and optimized capacities.

    A component is shown if it is already installed (``installed_capacity``
    greater than zero), or if it has a ``capex_spec`` or an ``opex_spec``
    greater than zero and an optimized capacity above ``threshold``.  Buses,
    demands, commodities and other components that are neither installed nor
    optimized with costs are left out.

    The optimized capacity of a component is taken from the ``"invest"``
    entry of ``imported_results``.

    Parameters
    ----------
    imported_results : ImportResults
        Imported results object, whose ``"invest"`` entry is used.
    es : EnergySystem
        Energy system the results belong to.
    threshold : float, optional
        Optimized capacities less than or equal to this value count as not
        optimized, which removes solver noise.  Defaults to 1e-6.

    Returns
    -------
    plotly.graph_objects.Figure
        Bar chart with one bar per shown component.  Installed components
        are hatched, optimized components are solid.  The legend separates
        the two types.
    """
    owners = _owner_map(es)
    optimized_capacity = {}
    if "invest" in imported_results and not imported_results["invest"].empty:
        for column, value in imported_results["invest"].iloc[0].items():
            owner = _owner_of_parts(_column_parts(column), owners)
            if owner is None or owner in optimized_capacity or not value:
                continue
            optimized_capacity[owner] = float(value)

    components = []
    installed = []
    optimized = []
    for node in es.nodes:
        if getattr(node, "parent", None) is not None:
            continue
        installed_capacity = getattr(node, "installed_capacity", None) or 0.0
        capex_spec = getattr(node, "capex_spec", None) or 0.0
        opex_spec = getattr(node, "opex_spec", None) or 0.0
        optimized_value = optimized_capacity.get(node, 0.0)
        is_installed = installed_capacity > 0
        is_optimized = optimized_value > threshold
        has_costs = capex_spec > 0 or opex_spec > 0
        if not (is_installed or (has_costs and is_optimized)):
            continue
        components.append(str(node.label))
        installed.append(installed_capacity)
        optimized.append(optimized_value if is_optimized else 0.0)

    fig = go.Figure()

    capacities = [
        inst if inst > 0 else opt
        for inst, opt in zip(installed, optimized, strict=True)
    ]

    installed_caps = [
        cap if inst > 0 else None
        for cap, inst in zip(capacities, installed, strict=True)
    ]
    optimized_caps = [
        cap if inst == 0 else None
        for cap, inst in zip(capacities, installed, strict=True)
    ]

    fig.add_bar(
        x=components,
        y=installed_caps,
        name="Installed",
        marker={
            "color": "#d64e12",
            "pattern": {
                "shape": "x",
                "fgcolor": "#d64e12",
                "bgcolor": "rgba(0,0,0,0)",
            },
        },
        customdata=[
            None if cap is None else _format_number(cap, 1)
            for cap in installed_caps
        ],
        hovertemplate=(
            "%{x}<br>Type: Installed<br>Capacity: %{customdata}<extra></extra>"
        ),
    )
    fig.add_bar(
        x=components,
        y=optimized_caps,
        name="Optimized",
        marker={"color": "#d64e12"},
        customdata=[
            None if cap is None else _format_number(cap, 1)
            for cap in optimized_caps
        ],
        hovertemplate=(
            "%{x}<br>Type: Optimized<br>Capacity: %{customdata}<extra></extra>"
        ),
    )

    fig.update_layout(
        barmode="overlay",
        showlegend=True,
        xaxis_title="Component",
        yaxis_title="Capacity",
        margin={"b": 150},
        title="Installed and Optimized Capacities",
    )

    return fig


def plot_annual_costs(
    results,
    es,
    unit="EUR",
    title="Annual project costs",
) -> go.Figure:
    """Plot the yearly project costs per component as a stacked bar chart.

    The cost table is created with
    :func:`oemof.eesyplan.postprocessing.KPIs.yearly_project_costs`.  Each
    component is one column, stacked by the three cost types.  Negative
    costs are drawn downwards from zero.  The cost types are told apart
    by their fill pattern: the annualized investment cost is solid, the
    fix operational costs carry an ``x`` hatch and the dispatch costs a
    ``/`` hatch.

    Parameters
    ----------
    results : ImportResults
        Imported results object.
    es : EnergySystem
        Energy system the results belong to.
    unit : str, optional
        Unit shown in the axis title and hover labels.  Defaults to "EUR".
    title : str, optional
        Figure title.  Defaults to "Annual project costs".

    Returns
    -------
    plotly.graph_objects.Figure
        Stacked bar chart with one column per component.
    """
    yearly_project_costs(results, es)
    table = _eesyplan_kpis(results)["yearly_project_costs"]
    table = table[table["component"] != "total"].copy()

    fig = go.Figure()
    for column, pattern in zip(_COST_COLUMNS, _COST_PATTERNS, strict=True):
        fig.add_bar(
            x=table["component"].astype(str),
            y=table[column],
            name=column,
            marker=_cost_type_marker("#d64e12", pattern),
            customdata=[_format_number(value, 0) for value in table[column]],
            hovertemplate=(
                f"<b>%{{x}}</b><br>{column}: %{{customdata}} {unit}"
                "<extra></extra>"
            ),
        )

    fig.update_layout(
        barmode="relative",
        title=title,
        xaxis_title="Component",
        yaxis_title=f"Annual costs [{unit}]",
        legend_title="Cost type",
        margin={"b": 150},
    )

    return fig


def compare_annual_costs(
    datasets,
    unit="EUR",
    title="Annual project costs by scenario",
) -> go.Figure:
    """Compare the yearly project costs of several scenarios.

    ``datasets`` maps the name of a scenario to its ``(results, es)``
    pair.  The costs of every scenario are calculated with
    :func:`oemof.eesyplan.postprocessing.KPIs.yearly_project_costs` and
    plotted like in :func:`plot_annual_costs`: one bar per component,
    stacked by the three cost types.

    Components usually have different names in the different scenarios,
    so the bars are grouped by their component type (the class of the
    component, e.g. ``WindTurbine``).  Bars of the same type sit next to
    each other, separated by a gap from the next type.  Every scenario
    has its own colour and one legend entry; the cost types are told
    apart by their fill pattern as in :func:`plot_annual_costs` and are
    spelled out in the hover text.

    Parameters
    ----------
    datasets : dict
        Maps the scenario name to a ``(results, es)`` tuple of that
        scenario.
    unit : str, optional
        Unit shown in the axis title and hover labels.  Defaults to
        "EUR".
    title : str, optional
        Figure title.  Defaults to "Annual project costs by scenario".

    Returns
    -------
    plotly.graph_objects.Figure
        Stacked bar chart with one bar per component and scenario.

    Raises
    ------
    ValueError
        If ``datasets`` is empty or an entry is no ``(results, es)``
        pair.
    """
    if not datasets:
        raise ValueError(
            "datasets must map at least one scenario to (results, es)."
        )
    for name, dataset in datasets.items():
        if not isinstance(dataset, list | tuple) or len(dataset) != 2:
            raise ValueError(
                f"The entry of '{name}' must be a (results, es) pair."
            )

    # one entry per bar: (scenario, node, component type, table row)
    bars = []
    for scenario, (results, es) in datasets.items():
        yearly_project_costs(results, es)
        table = _eesyplan_kpis(results)["yearly_project_costs"]
        table = table[table["component"] != "total"]
        owners = _owner_map(es)
        for _, row in table.iterrows():
            node = owners.get(row["component"])
            type_name = type(node).__name__ if node is not None else "other"
            bars.append((scenario, node, type_name, row))

    def _type_group_key(bar):
        index = _component_type_index(bar[1])
        return (index is None, index or 0, bar[2])

    bars.sort(key=_type_group_key)

    # numeric x positions: bars of one type sit next to each other, one
    # empty position separates the type groups
    tickvals = []
    ticktext = []
    position = 0
    previous_type = None
    plot_bars = []
    for scenario, _node, type_name, row in bars:
        if previous_type is not None and type_name != previous_type:
            position += 1
        plot_bars.append(
            {
                "position": position,
                "scenario": scenario,
                "type": type_name,
                "component": str(row["component"]),
                "row": row,
            }
        )
        tickvals.append(position)
        ticktext.append(str(row["component"]))
        previous_type = type_name
        position += 1

    scenario_colors = {
        scenario: qualitative.Plotly[index % len(qualitative.Plotly)]
        for index, scenario in enumerate(datasets)
    }

    fig = go.Figure()
    for scenario in datasets:
        color = scenario_colors[scenario]
        own = [bar for bar in plot_bars if bar["scenario"] == scenario]
        x = [bar["position"] for bar in own]
        for index, (column, pattern) in enumerate(
            zip(_COST_COLUMNS, _COST_PATTERNS, strict=True)
        ):
            fig.add_bar(
                x=x,
                y=[float(bar["row"][column]) for bar in own],
                name=scenario,
                legendgroup=scenario,
                showlegend=index == 0,
                marker=_cost_type_marker(color, pattern),
                customdata=[
                    [
                        bar["component"],
                        bar["type"],
                        _format_number(bar["row"][column], 0),
                    ]
                    for bar in own
                ],
                hovertemplate=(
                    f"<b>%{{customdata[0]}}</b><br>"
                    f"Scenario: {scenario}<br>"
                    "Component type: %{customdata[1]}<br>"
                    f"{column}: %{{customdata[2]}} {unit}"
                    "<extra></extra>"
                ),
            )

    fig.update_layout(
        barmode="relative",
        title=title,
        xaxis_title="Component",
        yaxis_title=f"Annual costs [{unit}]",
        legend_title="Scenario",
        margin={"b": 150},
    )
    if tickvals:
        fig.update_xaxes(tickvals=tickvals, ticktext=ticktext)
    return fig


def plot_timeseries(results, es, threshold=0.01, unit="kWh"):
    """Plot the input and output time series of every bus.

    A dropdown switches between the buses of ``es``.  Incoming flows are
    drawn as filled stacked areas, outgoing flows as lines.  Flows whose
    total is not larger than ``threshold`` are omitted, so only buses
    and edges that actually carry energy are shown.  Only ``CarrierBus``
    nodes are offered, internal buses are skipped.

    Parameters
    ----------
    results : ImportResults or pandas.DataFrame
        Imported results object, whose ``"flow"`` entry is used, or the
        flow DataFrame itself.
    es : EnergySystem
        Energy system the results belong to.  Its buses define the
        dropdown entries.
    threshold : float, optional
        Flows with a total sum smaller than or equal to this value are
        omitted.  Defaults to 0.01.
    unit : str, optional
        Unit shown in the axis title and the hover labels.  Defaults to
        "kWh".

    Returns
    -------
    plotly.graph_objects.Figure
        Figure with one dropdown entry per bus that carries a flow.
    """
    flows = results if isinstance(results, pd.DataFrame) else results["flow"]

    color_template = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    ]

    edges = []
    for column in flows.columns:
        parts = column if isinstance(column, tuple) else (column,)
        if len(parts) != 2:
            continue
        start, end = (_facade_label(part) for part in parts)
        if start == end:
            continue
        series = flows[column]
        if series.sum() <= threshold:
            continue
        edges.append((start, end, series))

    colors = {
        (start, end): color_template[index % len(color_template)]
        for index, (start, end, _) in enumerate(edges)
    }

    fig = go.Figure()
    traces_per_bus = {}

    for bus in (node for node in es.nodes if isinstance(node, CarrierBus)):
        bus_label = _facade_label(bus)
        inputs = [
            (start, end, series)
            for start, end, series in edges
            if end == bus_label
        ]
        outputs = [
            (start, end, series)
            for start, end, series in edges
            if start == bus_label
        ]
        if not inputs and not outputs:
            continue

        trace_indices = []
        for start, end, series in inputs:
            color = colors[(start, end)]
            fig.add_trace(
                go.Scatter(
                    x=series.index,
                    y=series.clip(lower=0),
                    customdata=[
                        _format_number(y, 1) for y in series.clip(lower=0)
                    ],
                    mode="none",
                    stackgroup=f"{bus_label}-inputs",
                    name=f"from {start}",
                    fillcolor=_rgba(color, 0.3),
                    line={"color": color},
                    visible=False,
                    hovertemplate=(
                        f"from {start}: %{{customdata}} {unit}<extra></extra>"
                    ),
                    hoverlabel={"align": "left"},
                )
            )
            trace_indices.append(len(fig.data) - 1)

        for start, end, series in outputs:
            color = colors[(start, end)]
            fig.add_trace(
                go.Scatter(
                    x=series.index,
                    y=series.clip(lower=0),
                    customdata=[
                        _format_number(y, 1) for y in series.clip(lower=0)
                    ],
                    mode="lines",
                    stackgroup=f"{bus_label}-outputs",
                    name=f"to {end}",
                    line={"color": color, "width": 2},
                    fill="none",
                    visible=False,
                    hovertemplate=(
                        f"to {end}: %{{customdata}} {unit}<extra></extra>"
                    ),
                    hoverlabel={"align": "left"},
                )
            )
            trace_indices.append(len(fig.data) - 1)

        traces_per_bus[bus_label] = trace_indices

    if not traces_per_bus:
        raise ValueError(
            f"No bus flows above the threshold of {threshold} were found."
        )

    buttons = []
    for bus_label, trace_indices in traces_per_bus.items():
        visible = [False] * len(fig.data)
        for index in trace_indices:
            visible[index] = True
        buttons.append(
            {
                "label": bus_label,
                "method": "update",
                "args": [
                    {"visible": visible},
                    {"title": {"text": f"Energy flows in {bus_label}"}},
                ],
            }
        )

    first_bus = next(iter(traces_per_bus))
    for index in traces_per_bus[first_bus]:
        fig.data[index].visible = True

    fig.update_layout(
        title={"text": f"Energy flows in {first_bus}"},
        xaxis_title="",
        yaxis_title=f"Energy flow [{unit}]",
        hovermode="x unified",
        showlegend=True,
        legend_title="Time series",
        legend={"x": 1.02, "y": 0.9, "xanchor": "left", "yanchor": "top"},
        updatemenus=[
            {
                "active": 0,
                "buttons": buttons,
                "x": 1.02,
                "y": 1.0,
                "xanchor": "left",
                "yanchor": "top",
            }
        ],
    )

    return fig


def plot_energy_mix(results, es, threshold=0.1, unit="MWh"):
    """Show the accumulated energy supply of the system as a donut chart.

    The supply of a source is the sum of all its outgoing flows over the
    whole time horizon.  Sources that do not supply a relevant amount of
    energy are omitted.

    Parameters
    ----------
    results : ImportResults or pandas.DataFrame
        Imported results object, whose ``"flow"`` entry is used, or the
        flow DataFrame itself.
    es : EnergySystem
        Energy system the results belong to.  Its sources define the
        slices of the chart.
    threshold : float, optional
        Sources with a total supply smaller than or equal to this value
        are omitted.  Defaults to 0.1.
    unit : str, optional
        Unit of the accumulated energy.  One of "Wh", "MWh" or "GWh".
        Defaults to "MWh".

    Returns
    -------
    plotly.graph_objects.Figure
        Donut chart with one slice per source.
    """
    flows = results if isinstance(results, pd.DataFrame) else results["flow"]

    divisor = {"Wh": 1.0, "MWh": 1000.0, "GWh": 1e6}[unit]

    source_labels = {
        clean_label(node): _facade_label(node)
        for node in es.nodes
        if isinstance(node, Source) and not isinstance(node, Shortage)
    }

    totals = {}
    for column in flows.columns:
        parts = column if isinstance(column, tuple) else (column,)
        if len(parts) != 2:
            continue
        label = clean_label(parts[0])
        if label not in source_labels:
            continue
        totals[label] = totals.get(label, 0.0) + float(flows[column].sum())

    labels = []
    values = []
    for label, total in totals.items():
        if total <= threshold:
            continue
        labels.append(source_labels[label])
        values.append(total / divisor)

    if not values:
        raise ValueError("No energy supply found in the results.")

    index = flows.index
    if isinstance(index, pd.DatetimeIndex) and len(index):
        period = f" from {index[0]:%Y-%m-%d} to {index[-1]:%Y-%m-%d}"
    else:
        period = ""

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.3,
                textinfo="label+percent",
                textposition="outside",
                hoverinfo="label+value+percent",
                hovertemplate=(
                    f"%{{label}}: %{{customdata}} {unit} (%{{percent}})"
                    "<extra></extra>"
                ),
                customdata=[_format_number(v, 1) for v in values],
            )
        ]
    )

    fig.update_layout(
        title=f"Accumulated energy supply of the system{period}",
        legend_title="Energy source",
    )

    return fig


def plot_renewable_vs_nonrenewable(results, es, threshold=0.1, unit="MWh"):
    """Show renewable and non-renewable energy supply side by side.

    The supply of a source is the sum of all its outgoing flows over the
    whole time horizon.  Sources with a fractional renewable share, such
    as a DSO, contribute their renewable and non-renewable parts to the
    respective chart.  Internal sources are folded into their facade.

    Parameters
    ----------
    results : ImportResults or pandas.DataFrame
        Imported results object, whose ``"flow"`` entry is used, or the
        flow DataFrame itself.
    es : EnergySystem
        Energy system the results belong to.  Its sources define the
        slices of the charts.
    threshold : float, optional
        Source contributions with an energy smaller than or equal to this
        value are omitted.  Defaults to 0.1.
    unit : str, optional
        Unit of the accumulated energy.  One of "Wh", "MWh" or "GWh".
        Defaults to "MWh".

    Returns
    -------
    plotly.graph_objects.Figure
        Stacked column chart with one column for renewable and one for
        non-renewable energy supply.
    """
    flows = results if isinstance(results, pd.DataFrame) else results["flow"]

    divisor = {"Wh": 1.0, "MWh": 1000.0, "GWh": 1e6}[unit]

    source_info = {
        clean_label(node): (
            _facade_label(node),
            _renewable_fraction(node),
        )
        for node in es.nodes
        if isinstance(node, Source) and not isinstance(node, Shortage)
    }

    renewable_totals = {}
    nonrenewable_totals = {}
    for column in flows.columns:
        parts = column if isinstance(column, tuple) else (column,)
        if len(parts) != 2:
            continue
        label = clean_label(parts[0])
        if label not in source_info:
            continue
        facade_label, renewable_fraction = source_info[label]
        energy = float(flows[column].sum())
        renewable_totals[facade_label] = (
            renewable_totals.get(facade_label, 0.0)
            + energy * renewable_fraction
        )
        nonrenewable_totals[facade_label] = nonrenewable_totals.get(
            facade_label, 0.0
        ) + energy * (1.0 - renewable_fraction)

    renewable = [
        (label, total / divisor)
        for label, total in renewable_totals.items()
        if total / divisor > threshold
    ]
    nonrenewable = [
        (label, total / divisor)
        for label, total in nonrenewable_totals.items()
        if total / divisor > threshold
    ]

    if not renewable and not nonrenewable:
        raise ValueError("No energy supply found in the results.")

    index = flows.index
    if isinstance(index, pd.DatetimeIndex) and len(index):
        period = f" from {index[0]:%Y-%m-%d} to {index[-1]:%Y-%m-%d}"
    else:
        period = ""

    total_renewable = sum(value for _, value in renewable)
    total_nonrenewable = sum(value for _, value in nonrenewable)
    max_total = max(total_renewable, total_nonrenewable)

    source_colors = {}
    for data in (renewable, nonrenewable):
        for label, _ in data:
            if label not in source_colors:
                source_colors[label] = qualitative.Plotly[
                    len(source_colors) % len(qualitative.Plotly)
                ]

    fig = go.Figure()
    shown_labels = set()
    charts = (
        ("Renewable", renewable),
        ("Non-renewable", nonrenewable),
    )
    for category, data in charts:
        for label, value in data:
            showlegend = label not in shown_labels
            shown_labels.add(label)
            fig.add_trace(
                go.Bar(
                    x=[category],
                    y=[value],
                    name=label,
                    legendgroup=label,
                    showlegend=showlegend,
                    marker_color=source_colors[label],
                    customdata=[_format_number(value, 1)],
                    hovertemplate=(
                        f"%{{x}}<br>%{{fullData.name}}: "
                        f"%{{customdata}} {unit}<extra></extra>"
                    ),
                )
            )

    for category, total in (
        ("Renewable", total_renewable),
        ("Non-renewable", total_nonrenewable),
    ):
        if total:
            fig.add_annotation(
                x=category,
                y=total,
                text=f"Total<br>{_format_number(total, 1)} {unit}",
                showarrow=False,
                yshift=10,
                yanchor="bottom",
            )
        else:
            fig.add_annotation(
                x=category,
                y=0,
                text="No energy supply",
                showarrow=False,
                yshift=10,
                yanchor="bottom",
            )

    fig.update_layout(
        width=900,
        height=600,
        title=f"Renewable vs non-renewable energy supply{period}",
        xaxis_title="",
        yaxis_title=f"Energy [{unit}]",
        yaxis_range=[0, max_total * 1.12 if max_total else 1],
        xaxis={
            "type": "category",
            "categoryorder": "array",
            "categoryarray": ["Renewable", "Non-renewable"],
        },
        barmode="stack",
        bargap=0.45,
        legend_title="Energy source",
    )

    return fig
