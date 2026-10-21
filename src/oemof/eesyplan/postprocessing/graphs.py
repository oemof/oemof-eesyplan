import re

import pandas as pd
import plotly.graph_objects as go
from oemof.solph.components import Source

from oemof.eesyplan import CarrierBus
from oemof.eesyplan import EnergySystem
from oemof.eesyplan import Shortage
from oemof.eesyplan.postprocessing.KPIs import clean_label


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
        int(color.lstrip("#")[index : index + 2], 16)
        for index in (0, 2, 4)
    )
    return f"rgba({red}, {green}, {blue}, {alpha})"


def _facade_label(part):
    """Return the label without an internal component prefix.

    Internal components carry tuple labels such as
    ``("consumption_converter", "Gasversorger")``.  Only the facade part
    is relevant for the legend.
    """
    return clean_label(part).rsplit(" | ", 1)[-1]


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
                    mode="none",
                    stackgroup=f"{bus_label}-inputs",
                    name=f"from {start}",
                    fillcolor=_rgba(color, 0.3),
                    line={"color": color},
                    visible=False,
                    hovertemplate=(
                        f"from {start}: %{{y:.1f}} {unit}<extra></extra>"
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
                    mode="lines",
                    stackgroup=f"{bus_label}-outputs",
                    name=f"to {end}",
                    line={"color": color, "width": 2},
                    fill="none",
                    visible=False,
                    hovertemplate=(
                        f"to {end}: %{{y:.1f}} {unit}<extra></extra>"
                    ),
                    hoverlabel={"align": "left"},
                )
            )
            trace_indices.append(len(fig.data) - 1)

        traces_per_bus[bus_label] = trace_indices

    if not traces_per_bus:
        raise ValueError(
            "No bus flows above the threshold of "
            f"{threshold} were found."
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
                    f"%{{label}}: %{{value:.1f}} {unit} (%{{percent}})"
                    "<extra></extra>"
                ),
            )
        ]
    )

    fig.update_layout(
        title=f"Accumulated energy supply of the system{period}",
        legend_title="Energy source",
    )

    return fig
