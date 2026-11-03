import logging
import re

import pandas as pd

from oemof.eesyplan import CarrierBus
from oemof.eesyplan import Demand
from oemof.eesyplan import FuelDemand
from oemof.eesyplan import H2Demand
from oemof.eesyplan import HeatDemand
from oemof.solph.components import Source

# Empty pyomo solver metadata that older exports still contain. Newer ones
# expose the solver summary as ``results.solver`` instead of a result key.
META_KEYS = {"Problem", "Solution", "Solver"}

# Namespace in the results object that holds all calculated eesyplan KPIs.
EESYPLAN_KEY = "eesyplan"

# All eesyplan demand components (they are the sinks that consume energy).
DEMAND_TYPES = (Demand, FuelDemand, H2Demand, HeatDemand)


def calculate_all_kpis(results, es, project_duration=None):
    """Calculate every KPI and write it into the results object.

    The KPIs are stored one level below the results in
    ``results["eesyplan"]``. The order matters: :func:`LCOE` uses the
    ``total_cost`` calculated first.
    """
    total_cost(results, es)
    LCOE(results, es)
    renewable_share(results, es)
    yearly_project_costs(results, es)
    project_cost_table(results, es, project_duration=project_duration)


def _eesyplan_kpis(results):
    """Return the KPI dictionary stored under ``results["eesyplan"]``.

    Solved and imported results both keep their data in ``results._data``.
    Plain dictionaries and attribute-style result objects are supported as
    well. The dictionary is created if it does not exist yet.
    """
    if hasattr(results, "_data"):
        return results._data.setdefault(EESYPLAN_KEY, {})
    if isinstance(results, dict):
        return results.setdefault(EESYPLAN_KEY, {})
    try:
        kpis = results[EESYPLAN_KEY]
    except Exception:
        kpis = None
    if kpis is None:
        try:
            results[EESYPLAN_KEY] = {}
            kpis = results[EESYPLAN_KEY]
        except Exception:
            if not hasattr(results, EESYPLAN_KEY):
                setattr(results, EESYPLAN_KEY, {})
            kpis = getattr(results, EESYPLAN_KEY)
    return kpis


def _store_result(results, key, value):
    """Write one KPI into the ``eesyplan`` namespace of the results."""
    _eesyplan_kpis(results)[key] = value


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


def _solver_value(results, name):
    """Entry ``name`` of the solver summary ``results.solver`` or ``None``.

    Solved and imported results both carry the summary as a
    ``pandas.Series`` (``optimal``, ``termination_condition``,
    ``objective``, ``solver``, ...).
    """
    solver = getattr(results, "solver", None)
    if solver is None:
        return None
    if hasattr(solver, "get"):
        try:
            val = solver.get(name)
            if val is not None:
                return val
        except Exception:
            logging.debug("Could not read '%s' from the solver summary.", name)
    if hasattr(solver, name):
        try:
            return getattr(solver, name)
        except Exception:
            logging.debug("Could not read '%s' from the solver summary.", name)
    if isinstance(solver, dict):
        try:
            return solver.get(name)
        except Exception:
            logging.debug("Could not read '%s' from the solver summary.", name)
    # try __getitem__
    try:
        return solver[name]
    except Exception:
        logging.debug("Could not read '%s' from the solver summary.", name)
    return None


def get_objective(results):
    """Objective value (total system cost) of a solved or imported result.

    The objective is not a regular result key, it is part of the solver
    summary ``results.solver``. Imported results read that summary from a
    CSV file, so the value arrives as text and is converted to ``float``
    here. Results of older exports that still store a plain ``objective``
    key are supported as well.

    Raises
    ------
    ValueError
        If the results contain no objective, e.g. because they were
        exported with an oemof-datapackage that does not write the solver
        summary yet.
    """
    value = _solver_value(results, "objective")
    if value is None and "objective" in results.keys():
        value = results["objective"]
    try:
        objective = float(value)
    except (TypeError, ValueError):
        objective = float("nan")
    if pd.isna(objective):
        raise ValueError(
            "The results contain no objective. Export them again with an "
            "up-to-date oemof-datapackage, which stores the solver summary "
            "including the objective as 'solver.csv'."
        )
    return objective


def LCOE(results, es):
    """Levelised cost of energy = total cost / total energy into the demands.

    The total cost is read from ``results["eesyplan"]["total_cost"]``, so
    :func:`total_cost` has to be calculated first. It includes the solver
    objective, the annual fixed costs of installed capacities and the
    flat fix costs of the components.

    The demand nodes cannot be told apart from the results alone (internal
    sinks such as ``feedin_sink`` look the same), so the energy system is
    needed to identify them. Sum the flow of every edge that ends in a
    demand node, then divide the system cost by that energy.

    The result is written to ``results["eesyplan"]["lcoe"]``. The readable
    ``(from, to)`` labels of every summed flow are written to
    ``results["eesyplan"]["lcoe_considered_flows"]``.
    """
    kpis = _eesyplan_kpis(results)
    if "total_cost" not in kpis:
        raise KeyError(
            "The KPI 'total_cost' is missing. Calculate it before the LCOE, "
            "e.g. with calculate_all_kpis(results, es)."
        )

    demands = demand_labels(es)
    flows = results["flow"]
    considered_flows = [
        column for column in flows.columns if clean_label(column[1]) in demands
    ]
    total_demand = sum(flows[column].sum() for column in considered_flows)

    _store_result(results, "lcoe", kpis["total_cost"] / total_demand)
    _store_result(
        results,
        "lcoe_considered_flows",
        [
            (clean_label(column[0]), clean_label(column[1]))
            for column in considered_flows
        ],
    )


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

    The result is written to ``results["eesyplan"]["renewable_share"]``.
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

    _store_result(results, "renewable_share", renewable_energy / total_energy)


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

    Returns ``(components, capacity, investment_cost, variable,
    fix_investment_ann, fix_annual)`` where all but the first are dicts
    keyed by the top-level component node (``components`` is a list):

    capacity            optimised capacity from ``invest``
    investment_cost     annual model cost from ``investment_costs``
                        (annualised capex + fixed opex)
    variable            variable costs summed over the whole horizon
    fix_investment_ann  annualised ``investment_fix_cost`` (a flat cost
                        that is not tied to a capacity)
    fix_annual          ``annual_fix_cost`` per year (flat as well)
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

    fix_investment_ann, fix_annual = _fix_cost_data(es, capacity)

    return (
        components,
        capacity,
        investment_cost,
        variable,
        fix_investment_ann,
        fix_annual,
    )


def _fix_cost_data(es, capacity):
    """Flat fix costs of every component, annualised where needed.

    Components can carry two flat costs that are not tied to a capacity:
    ``investment_fix_cost`` (one-time, annualised here) and
    ``annual_fix_cost`` (per year). Both are counted for every component
    that defines them, even if its capacity is zero. A component without
    any capacity is unusual, so it is reported with a warning.

    Returns ``(fix_investment_ann, fix_annual)`` dicts keyed by the
    top-level component node. The result is cached on the energy system
    so that the warnings are logged only once per component.
    """
    cached = getattr(es, "_eesyplan_fix_costs", None)
    if cached is not None:
        return cached

    fix_investment_ann = {}
    fix_annual = {}
    for node in es.nodes:
        if getattr(node, "parent", None) is not None:
            continue
        investment_fix_cost = getattr(node, "investment_fix_cost", None)
        annual_fix_cost = getattr(node, "annual_fix_cost", None)
        if not investment_fix_cost and not annual_fix_cost:
            continue
        if annual_fix_cost:
            fix_annual[node] = float(annual_fix_cost)
        if investment_fix_cost:
            fix_investment_ann[node] = _annualized_fix_investment(
                node, es, capacity, investment_fix_cost
            )
        if _effective_capacity(node, capacity) == 0:
            logging.warning(
                "Component '%s' carries fix costs but has no capacity. "
                "The fix costs are counted anyway.",
                _norm_label(node.label),
            )

    cached = (fix_investment_ann, fix_annual)
    try:
        es._eesyplan_fix_costs = cached
    except AttributeError:
        logging.debug(
            "The energy system does not accept attributes. The fix cost "
            "warnings will be logged again on the next call."
        )
    return cached


def _annualized_fix_investment(node, es, capacity, investment_fix_cost):
    """Annualised ``investment_fix_cost`` of one component.

    The annuity is calculated with the project data (tax and discount
    factor), like the capex of installed components in
    :func:`_component_costs`. Components that already exist pay the fix
    investment cost of their replacement, so the replacement timing
    ``year_of_investment = lifetime - age_installed`` is used. New
    components invest in year 0.

    Fallbacks, each reported with a warning:

    lifetime        ``economic_period`` of the project, or 20 if none is
                    available
    age_installed   0
    project data    linear annualisation ``investment_fix_cost /
                    lifetime`` without tax and discounting
    """
    project = (
        getattr(node, "project_data", None)
        or getattr(node, "_project_data", None)
        or getattr(es, "project_data", None)
    )
    lifetime = getattr(node, "lifetime", None)
    if lifetime is None:
        lifetime = _economic_period(es) or 20
        logging.warning(
            "Component '%s' has no lifetime. Falling back to %s years "
            "(the economic_period of the project or 20) to annualize "
            "its investment_fix_cost.",
            _norm_label(node.label),
            lifetime,
        )
    age_installed = getattr(node, "age_installed", None)
    if age_installed is None:
        age_installed = 0
        logging.warning(
            "Component '%s' has no age_installed. Falling back to 0 "
            "years to annualize its investment_fix_cost.",
            _norm_label(node.label),
        )
    if project is None:
        logging.warning(
            "Component '%s' has no project data (tax, discount factor). "
            "Annualizing its investment_fix_cost linearly over %s years.",
            _norm_label(node.label),
            lifetime,
        )
        return float(investment_fix_cost) / lifetime

    installed = getattr(node, "installed_capacity", None)
    if installed and node not in capacity:
        year_of_investment = lifetime - age_installed
    else:
        year_of_investment = 0
    return float(
        project.calculate_annuity(
            investment_fix_cost,
            lifetime,
            year_of_investment=year_of_investment,
        )
    )


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


def _component_costs(
    node, capacity, investment_cost, fix_investment_ann=None, fix_annual=None
):
    """Annualised investment and fixed operational costs of a component.

    For optimised components the model bundles investment and fixed
    operation costs into a single annual ``investment_costs`` value.  The
    annuity is therefore reconstructed as ``investment_costs - opex``.

    Component Costs with an ``installed_capacity`` are not part of the
    optimisation.  They carry no investment in the model, so their
    replacement within the project duration is missing in the results.
    The annualised capex of that replacement is calculated from the
    component parameters.

    The flat fix costs ``investment_fix_cost`` (annualised) and
    ``annual_fix_cost`` are not tied to a capacity, so they are added to
    the investment and the fixed operational costs as they are.

    Returns
    -------
    tuple
        ``(annualised investment cost, fixed operational costs)``
    """
    fix_investment_ann = fix_investment_ann or {}
    fix_annual = fix_annual or {}
    installed = getattr(node, "installed_capacity", None)
    opex_spec = getattr(node, "opex_spec", None) or 0.0
    cap = _effective_capacity(node, capacity)

    base_opex = opex_spec * cap

    if installed and node not in capacity:
        # existing component: not optimised, so the model contains no
        # investment costs for it.  Only the replacement within the
        # project duration is left to be accounted for.
        installed_capex_spec_annualized = getattr(
            node, "installed_capex_spec_annualized", None
        )
        if installed_capex_spec_annualized is None:
            project_data = getattr(node, "project_data", None) or getattr(
                node, "_project_data", None
            )
            capex_spec = getattr(node, "capex_spec", None)
            lifetime = getattr(node, "lifetime", None)
            age_installed = getattr(node, "age_installed", 0) or 0
            if project_data is None or capex_spec is None or lifetime is None:
                installed_capex_spec_annualized = 0.0
            else:
                year_of_investment = lifetime - age_installed
                installed_capex_spec_annualized = (
                    project_data.calculate_annuity(
                        capex_spec,
                        lifetime,
                        year_of_investment=year_of_investment,
                    )
                )
        base_capex = float(installed_capex_spec_annualized or 0.0) * cap
    else:
        base_capex = investment_cost.get(node, 0.0) - base_opex

    component_capex = base_capex + fix_investment_ann.get(node, 0.0)
    component_opex = base_opex + fix_annual.get(node, 0.0)
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

    The flat fix costs ``investment_fix_cost`` (annualised) and
    ``annual_fix_cost`` are not tied to a capacity.  They are added to
    the annualized investment cost and to the fix operational costs.

    The table is written to ``results["eesyplan"]["yearly_project_costs"]``.
    It contains one row per component that carries a cost plus a final
    ``total`` row.  Components without any cost are omitted.
    """
    (
        components,
        capacity,
        investment_cost,
        variable,
        fix_investment_ann,
        fix_annual,
    ) = _component_cost_data(results, es)

    rows = []
    for node in components:
        component_capex, component_opex = _component_costs(
            node,
            capacity,
            investment_cost,
            fix_investment_ann,
            fix_annual,
        )
        rows.append(
            {
                "component": _norm_label(node.label),
                "annualized investment cost": component_capex,
                "fix operational costs": component_opex,
                "dispatch costs": variable.get(node, 0.0),
            }
        )

    _store_result(
        results,
        "yearly_project_costs",
        _cost_table(
            rows,
            [
                "annualized investment cost",
                "fix operational costs",
                "dispatch costs",
            ],
        ),
    )


def _economic_period(es):
    """Economic period of the project attached to the energy system."""
    projects = [getattr(es, "project_data", None)]
    projects.extend(
        getattr(node, "project_data", None)
        or getattr(node, "_project_data", None)
        for node in es.nodes
    )
    for project in projects:
        duration = getattr(project, "economic_period", None)
        if duration is not None:
            return duration
    return None


def _project_duration(es, project_duration=None):
    """Project duration from the energy system, with a warning fallback."""
    if project_duration is not None:
        return project_duration

    duration = _economic_period(es)
    if duration is not None:
        return duration

    logging.warning(
        "No economic_period found in the energy system. Falling back to a "
        "project duration of 20 years."
    )
    return 20


def project_cost_table(results, es, project_duration=None):
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

    The flat fix costs are included as well: the ``investment_fix_cost``
    of new components is part of the year 0 investment, its annualised
    value is part of the investment over the full project and the
    ``annual_fix_cost`` is part of the fixed operational costs.

    The project duration is read from the ``economic_period`` of the
    project attached to the energy system. If none is found, a warning is
    logged and 20 years are used. A duration can also be passed explicitly.

    The table is written to ``results["eesyplan"]["project_cost_table"]``.
    It contains one row per component that carries a cost plus a final
    ``total`` row.  Components without any cost are omitted.
    """
    project_duration = _project_duration(es, project_duration)
    (
        components,
        capacity,
        investment_cost,
        variable,
        fix_investment_ann,
        fix_annual,
    ) = _component_cost_data(results, es)

    rows = []
    for node in components:
        cap = capacity.get(node, 0.0)
        component_capex_ann, component_opex_ann = _component_costs(
            node,
            capacity,
            investment_cost,
            fix_investment_ann,
            fix_annual,
        )
        investment_year0 = (getattr(node, "capex_spec", None) or 0.0) * cap
        if not getattr(node, "installed_capacity", None):
            # new components pay their fix investment cost in year 0 as
            # well, existing ones paid it before the project started
            investment_year0 += (
                getattr(node, "investment_fix_cost", None) or 0.0
            )
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

    _store_result(
        results,
        "project_cost_table",
        _cost_table(
            rows,
            [
                "investment cost in year 0 (not including reinvestment)",
                "investment cost over the full project (including reinvestments)",
                "fix operational costs over project duration",
                "dispatch costs over project duration",
            ],
        ),
    )


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

    The fix disables itself as soon as the import provides the data
    correctly. The objective needs no patching anymore, it is read from the
    solver summary by :func:`get_objective`.
    """
    # TODO: temporary fix until variable_costs is exported/imported correctly.
    if "variable_costs" in results:
        costs = results["variable_costs"]
        if isinstance(costs, pd.DataFrame) and not costs.empty:
            try:
                costs.to_numpy(dtype=float)
            except (TypeError, ValueError):
                results._data["variable_costs"] = _numeric_variable_costs(
                    costs
                )


def _additional_installed_costs(results, es):
    """Annual costs that are missing in the solver objective.

    Two kinds of costs never reach the objective: the annual fixed costs
    of already installed capacities (they are not part of the
    optimisation) and the flat fix costs of the components
    (``investment_fix_cost``, annualised, and ``annual_fix_cost``),
    which cannot be mapped onto a capacity and are therefore unknown to
    the model.
    """
    (
        components,
        capacity,
        investment_cost,
        _variable,
        fix_investment_ann,
        fix_annual,
    ) = _component_cost_data(results, es)
    additional_fixed_costs = 0.0
    for node in components:
        installed = getattr(node, "installed_capacity", None)
        if installed and node not in capacity:
            component_capex, component_opex = _component_costs(
                node,
                capacity,
                investment_cost,
                fix_investment_ann,
                fix_annual,
            )
            additional_fixed_costs += component_capex + component_opex
        else:
            # optimised components are already covered by the objective,
            # only their flat fix costs are missing
            additional_fixed_costs += fix_investment_ann.get(
                node, 0.0
            ) + fix_annual.get(node, 0.0)
    return additional_fixed_costs


def total_cost(results, es):
    """Total cost of the energy system.

    The solver objective only contains the costs of the optimisation.
    The annual fixed costs of already installed capacities and the flat
    fix costs of the components (``investment_fix_cost``, annualised,
    and ``annual_fix_cost``) are missing, so they are added here.

    The result is written to ``results["eesyplan"]["total_cost"]``.
    """
    objective = get_objective(results)
    _store_result(
        results,
        "total_cost",
        objective + _additional_installed_costs(results, es),
    )
