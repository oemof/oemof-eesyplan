import re

import pandas as pd
from oemof.solph.components import Source

from oemof.eesyplan import CarrierBus
from oemof.eesyplan import Demand
from oemof.eesyplan import FuelDemand
from oemof.eesyplan import H2Demand
from oemof.eesyplan import HeatDemand

# Empty pyomo solver metadata that is exported but carries no information.
META_KEYS = {"Problem", "Solution", "Solver"}

# All eesyplan demand components (they are the sinks that consume energy).
DEMAND_TYPES = (Demand, FuelDemand, H2Demand, HeatDemand)


def clean_label(part):
    """Turn a raw column label into a readable string.

    Imported results label columns in several flavours:
      - plain labels ............ "Strom_bus"
      - stringified tuples ...... "('feedin_converter', 'Stromversorger')"
      - oemof reprs ............. "<...HeatPump: 'Luft-Wärmepumpe'>"
      - CarrierBus reprs ........ "<CarrierBus 'Wärme_bus', carrier='Heat', ...>"
    """
    text = str(part)
    text = re.sub(r"carrier='[^']*'", "", text)
    text = re.sub(r"(shortage|excess):\s*\w+", "", text)
    tokens = re.findall(r"'([^']*)'", text)
    if tokens:
        return " | ".join(tokens)
    return text.strip('"').strip("'")


def edge_label(column):
    """Readable (from, to) label of one flow column."""
    return clean_label(column[0]), clean_label(column[1])


def result_keys(results):
    """Keys of the imported results without the empty solver metadata."""
    return [k for k in sorted(results.keys()) if k not in META_KEYS]


def demand_labels(es):
    """Labels of every demand (sink) node of the energy system."""
    return {node.label for node in es.nodes if isinstance(node, DEMAND_TYPES)}


def LCOE(results, es):
    """Levelised cost of energy = objective / total energy into the demands.

    The demand nodes cannot be told apart from the results alone (internal
    sinks such as ``feedin_sink`` look the same), so the energy system is
    needed to identify them. Sum the flow of every edge that ends in a
    demand node, then divide the system cost by that energy.

    Returns
    -------
    lcoe : float
        Levelised cost of energy.
    considered_flows : list of tuple
        The ``(from, to)`` column tuples of every flow that was summed.
    """
    demands = demand_labels(es)
    flows = results["flow"]
    considered_flows = [
        column
        for column in flows.columns
        if clean_label(column[1]) in demands
    ]
    total_demand = sum(flows[column].sum() for column in considered_flows)
    return results["objective"] / total_demand, considered_flows


def _norm_label(label):
    """Normalise a node label to the same text ``clean_label`` produces."""
    if isinstance(label, tuple):
        return " | ".join(_norm_label(part) for part in label)
    return str(label)


def _renewable_fraction(node):
    """Renewable fraction of a node.

    ``renewable_asset=True`` -> 1.0, ``renewable_asset=False`` -> 0.0,
    else ``renewable_share`` if present, else 0.0. The value is looked up
    on the node itself and then on its parent components, so internal
    sources (e.g. the DSO's ``consumption_source``) inherit the
    ``renewable_share`` of their DSO.
    """
    current = node
    while current is not None:
        if getattr(current, "renewable_asset", None) is not None:
            return 1.0 if current.renewable_asset else 0.0
        if getattr(current, "renewable_share", None) is not None:
            return float(current.renewable_share)
        current = getattr(current, "parent", None)
    return 0.0


def renewable_share(results, es):
    """Total renewable share of all energy produced or bought.

    Every source node is taken into account: the top-level production
    plants as well as internal sources such as the DSO's
    ``consumption_source``. For each source the produced/bought energy
    (sum of its outgoing flows) is weighted with its renewable fraction
    and divided by the total energy of all sources.
    """
    flows = results["flow"]
    total_energy = 0.0
    renewable_energy = 0.0

    for node in es.nodes:
        if not isinstance(node, Source):
            continue
        label = _norm_label(node.label)
        energy = sum(
            flows[column].sum()
            for column in flows.columns
            if clean_label(column[0]) == label
        )
        total_energy += energy
        renewable_energy += energy * _renewable_fraction(node)

    return renewable_energy / total_energy


def describe_results(results):
    """Print the structure of the imported results object.

    The current result object no longer exposes an ``objective`` entry.
    This lists exactly the keys that are available and their structure.
    """
    print("=" * 78)
    print("IMPORTED RESULTS - STRUCTURE")
    print("=" * 78)
    print(f"type           : {type(results).__name__}")
    timeindex = results.timeindex
    print(f"timesteps      : {len(timeindex)}")
    if len(timeindex):
        print(f"first step     : {timeindex[0]}")
        print(f"last step      : {timeindex[-1]}")
    print()
    print(f"{'key':<20}{'kind':<13}{'shape':<14}{'index':<16}{'levels':<8}")
    print("-" * 78)
    for key in sorted(results.keys()):
        value = results[key]
        if not isinstance(value, pd.DataFrame):
            print(f"{key:<20}{type(value).__name__:<13}")
            continue
        if value.empty:
            kind = "empty"
        elif isinstance(value.index, pd.DatetimeIndex):
            kind = "time series"
        else:
            kind = "element"
        print(
            f"{key:<20}{kind:<13}{value.shape!s:<14}"
            f"{type(value.index).__name__:<16}{value.columns.nlevels:<8}"
        )
    print()


def print_flows(results):
    """Loop over every connection (edge) of the flow time series."""
    if "flow" not in results:
        return
    flows = results["flow"]
    print("Flows (energy over the whole horizon per connection):")
    for column in flows.columns:
        source, target = edge_label(column)
        energy = flows[column].sum()
        if energy != 0:
            print(f"  {source:>30} -> {target:<30} {energy:>14.2f}")
    print()


def print_storages(results):
    """Loop over every storage in the storage_content time series."""
    if "storage_content" not in results:
        return
    storage = results["storage_content"]
    print("Storage content:")
    for column in storage.columns:
        series = storage[column]
        print(
            f"  {clean_label(column):<30} "
            f"min={series.min():>12.2f} max={series.max():>12.2f}"
        )
    print()


def print_investments(results):
    """Loop over the optimized capacities (invest) and their costs."""
    if "invest" not in results:
        return
    print("Optimised capacities (invest) - one row, one column per node/edge:")
    invest = results["invest"].iloc[0]
    for column, value in invest.items():
        if value:
            print(f"  {clean_label(column):<55} {value:>12.3f}")
    print()

    if "investment_costs" in results:
        print("Annual investment costs:")
        costs = results["investment_costs"].iloc[0]
        for column, value in costs.items():
            if value:
                print(f"  {clean_label(column):<55} {value:>12.3f}")
        print()


def print_costs(results):
    """Loop over the variable costs per connection."""
    if "variable_costs" not in results:
        return
    costs = results["variable_costs"]
    print("Variable costs over the whole horizon per connection:")
    for column in costs.columns:
        source, target = edge_label(column)
        total = costs[column].sum()
        if total != 0:
            print(f"  {source:>30} -> {target:<30} {total:>14.2f}")
    print()


def _top_level_node(node):
    """Walk the ``parent`` chain up to the top-level component of a node."""
    top = node
    while getattr(top, "parent", None) is not None:
        top = top.parent
    return top


def _owner_map(es):
    """Map every node label (incl. subnodes) to its top-level component."""
    owners = {}
    for node in es.nodes:
        owners[_norm_label(node.label)] = _top_level_node(node)
    return owners


def _is_neutral(node):
    """Buses and demands only route/hold energy, they carry no investment."""
    return isinstance(node, CarrierBus) or isinstance(node, DEMAND_TYPES)


def _owner_of_parts(parts, owners):
    """Owner of a column: first non-neutral component among its labels."""
    candidates = [owners.get(part) for part in parts]
    for candidate in candidates:
        if candidate is not None and not _is_neutral(candidate):
            return candidate
    for candidate in candidates:
        if candidate is not None:
            return candidate
    return None


def _edge_owner(column, owners):
    """Owner of a flow ``(from, to)`` column."""
    source = owners.get(clean_label(column[0]))
    target = owners.get(clean_label(column[1]))
    if source is not None and not _is_neutral(source):
        return source
    return target if target is not None else source


def _column_parts(column):
    """Node labels contained in an ``invest``/``investment_costs`` column."""
    return [part for part in clean_label(column).split(" | ") if part]


def _component_cost_data(results, es):
    """Per-component cost building blocks, shared by both cost tables.

    Returns ``(components, capacity, investment_cost, variable)`` where
    the last three are dicts keyed by the top-level component node:

    capacity         optimised capacity from ``invest``
    investment_cost  annual model cost from ``investment_costs``
                     (annualised capex + fixed opex)
    variable         variable costs summed over the whole horizon
    """
    owners = _owner_map(es)
    components = [
        node for node in es.nodes if getattr(node, "parent", None) is None
    ]

    capacity = {}
    investment_cost = {}
    variable = {}

    # A single investment is exported under several columns (e.g. the
    # storage node plus both of its flows).  They always share the same
    # value, so the first non-zero one per component is enough.
    if "invest" in results:
        for column, value in results["invest"].iloc[0].items():
            owner = _owner_of_parts(_column_parts(column), owners)
            if owner is None or owner in capacity or not value:
                continue
            capacity[owner] = float(value)

    if "investment_costs" in results:
        for column, value in results["investment_costs"].iloc[0].items():
            owner = _owner_of_parts(_column_parts(column), owners)
            if owner is None or owner in investment_cost or not value:
                continue
            investment_cost[owner] = float(value)

    if "variable_costs" in results:
        costs = results["variable_costs"]
        for column in costs.columns:
            owner = _edge_owner(column, owners)
            if owner is None:
                continue
            variable[owner] = variable.get(owner, 0.0) + costs[column].sum()

    return components, capacity, investment_cost, variable


def _cost_table(rows, value_columns):
    """Turn per-component rows into a sorted table with a total row.

    Components without any cost are dropped.
    """
    table = pd.DataFrame(rows, columns=["component", *value_columns])
    table = table[(table[value_columns].abs() > 1e-9).any(axis=1)]
    table["total"] = table[value_columns].sum(axis=1)
    table = table.sort_values("total", ascending=False, ignore_index=True)

    total = table[[*value_columns, "total"]].sum()
    total_row = pd.DataFrame([{"component": "total", **total.to_dict()}])
    return pd.concat([table, total_row], ignore_index=True)


def _effective_capacity(node, capacity):
    """Capacity of a component that is relevant for its costs.

    Optimised components use their optimised capacity.  Components with
    an ``installed_capacity`` are not optimised, so their installed
    capacity is used instead.
    """
    installed = getattr(node, "installed_capacity", None)
    if installed and node not in capacity:
        return float(installed)
    return capacity.get(node, 0.0)


def _component_costs(node, capacity, investment_cost):
    """Annualised investment and fixed operational costs of a component.

    For optimised components the model bundles investment and fixed
    operation costs into a single annual ``investment_costs`` value.  The
    annuity is therefore reconstructed as ``investment_costs - opex``.

    Component Costs with an ``installed_capacity`` are not part of the
    optimisation.  They carry no investment in the model, so their
    replacement within the project duration is missing in the results.
    They provide the annualised capex of that replacement as
    ``installed_capex_spec_annualized``.

    Returns
    -------
    tuple
        ``(annualised investment cost, fixed operational costs)``
    """
    installed = getattr(node, "installed_capacity", None)
    opex_spec = getattr(node, "opex_spec", None) or 0.0
    cap = _effective_capacity(node, capacity)

    component_opex = opex_spec * cap

    if installed and node not in capacity:
        # existing component: not optimised, so the model contains no
        # investment costs for it.  Only the replacement within the
        # project duration is left to be accounted for.
        component_capex = (
            getattr(node, "installed_capex_spec_annualized", None) or 0.0
        ) * cap
    else:
        component_capex = investment_cost.get(node, 0.0) - component_opex

    return component_capex, component_opex


def yearly_project_costs(results, es):
    """Yearly project costs per component as a table.

    The model bundles investment and fixed operation costs into a single
    annual ``investment_costs`` value per component.  Because the annuity
    can not be recovered without the project data, it is reconstructed as

        capex = investment_costs - opex

    with ``opex = opex_spec * capacity``.  The columns are:

    component                   readable label of every top-level component
    annualized investment cost  annualised investment cost (annuity)
    fix operational costs       fixed operation & maintenance cost
    dispatch costs              sum of the variable costs of all flows of the
                                component over the whole horizon

    Components with an ``installed_capacity`` are not optimised and
    therefore carry no investment cost in the model.  Their replacement
    within the project duration is added as annualised investment cost
    (see :func:`_component_costs`).

    Returns
    -------
    pandas.DataFrame
        One row per component that carries a cost plus a final ``total``
        row.  Components without any cost are omitted.
    """
    components, capacity, investment_cost, variable = _component_cost_data(
        results, es
    )

    rows = []
    for node in components:
        component_capex, component_opex = _component_costs(
            node, capacity, investment_cost
        )
        rows.append(
            {
                "component": _norm_label(node.label),
                "annualized investment cost": component_capex,
                "fix operational costs": component_opex,
                "dispatch costs": variable.get(node, 0.0),
            }
        )

    return _cost_table(
        rows,
        [
            "annualized investment cost",
            "fix operational costs",
            "dispatch costs",
        ],
    )


def project_cost_table(results, es, project_duration=20):
    """Total project costs per component over the project duration.

    Unlike :func:`yearly_project_costs` this table is not annualised and
    spans the whole project duration (``economic_period``):

    component          readable label of every top-level component
    investment cost in year 0 (not including reinvestment)
                       one-time investment ``capex_spec * capacity``
    investment cost over the full project (including reinvestments)
                       ``annualized investment cost * project_duration``
    fix operational costs over project duration
                       ``opex_spec * capacity * project_duration``
    dispatch costs over project duration
                       yearly variable costs * ``project_duration``

    Components with an ``installed_capacity`` are not optimised.  They
    were built before the project, so they have no investment cost in
    year 0, but their operational costs are accounted for over the
    project duration.  Reinvestments for installed components are
    included based on their annualized replacement cost.

    The project duration is not part of the results or the energy
    system, so it has to be supplied by the caller.

    Returns
    -------
    pandas.DataFrame
        One row per component that carries a cost plus a final ``total``
        row.  Components without any cost are omitted.
    """
    components, capacity, investment_cost, variable = _component_cost_data(
        results, es
    )

    rows = []
    for node in components:
        cap = capacity.get(node, 0.0)
        component_capex_ann, component_opex_ann = _component_costs(
            node, capacity, investment_cost
        )
        investment_year0 = (getattr(node, "capex_spec", None) or 0.0) * cap
        investment_full = component_capex_ann * project_duration
        operational = component_opex_ann * project_duration
        rows.append(
            {
                "component": _norm_label(node.label),
                "investment cost in year 0 (not including reinvestment)": (
                    investment_year0
                ),
                "investment cost over the full project (including reinvestments)": (
                    investment_full
                ),
                "fix operational costs over project duration": operational,
                "dispatch costs over project duration": (
                    variable.get(node, 0.0) * project_duration
                ),
            }
        )

    return _cost_table(
        rows,
        [
            "investment cost in year 0 (not including reinvestment)",
            "investment cost over the full project (including reinvestments)",
            "fix operational costs over project duration",
            "dispatch costs over project duration",
        ],
    )


def print_cost_table(table, value_columns=None, title=""):
    """Print a cost table with a total column.

    If ``value_columns`` is not given, all columns except ``component``
    and ``total`` are used.  ``title`` may be omitted.
    """
    if value_columns is None:
        value_columns = [
            column for column in table.columns if column not in ("component", "total")
        ]
    component_width = max(
        26, max(len(str(value)) for value in table["component"]) + 2
    )
    width = max(18, max(len(column) for column in value_columns) + 2)
    if title:
        print(title)
    header = f"  {'component':<{component_width}}" + "".join(
        f"{column:>{width}}" for column in value_columns
    )
    print(header + f"{'total':>{width}}")
    print(
        "  "
        + "-" * (component_width + width * (len(value_columns) + 1))
    )
    for _, row in table.iterrows():
        line = f"  {row['component']:<{component_width}}" + "".join(
            f"{row[column]:>{width}.2f}" for column in value_columns
        )
        print(line + f"{row['total']:>{width}.2f}")
    print()


def _numeric_variable_costs(costs):
    """Decode imported ``variable_costs`` text back into numbers.

    Some exports contain text like ``"[0.0, 0.0, ..., 0.0]"`` instead of
    plain numbers.  The value represented by such a cell is its first number.
    """

    def to_float(value):
        if isinstance(value, str):
            match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", value)
            return float(match.group()) if match else float("nan")
        return float(value)

    return costs.map(to_float)


def normalize_imported_results(results):
    """Patch known gaps of the current result import.

    Both fixes disable themselves as soon as the import provides the data
    correctly.
    """
    # TODO: temporary placeholder until objective is exported/imported again.
    if "objective" not in results:
        results._data["objective"] = 20000.0

    # TODO: temporary fix until variable_costs is exported/imported correctly.
    if "variable_costs" in results:
        costs = results["variable_costs"]
        if isinstance(costs, pd.DataFrame) and not costs.empty:
            try:
                costs.to_numpy(dtype=float)
            except (TypeError, ValueError):
                results._data["variable_costs"] = _numeric_variable_costs(costs)
