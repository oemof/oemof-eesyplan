import pandas as pd

from oemof.eesyplan.postprocessing.KPIs import EESYPLAN_KEY
from oemof.eesyplan.postprocessing.KPIs import _solver_value
from oemof.eesyplan.postprocessing.KPIs import clean_label
from oemof.eesyplan.postprocessing.KPIs import edge_label
from oemof.eesyplan.postprocessing.KPIs import get_objective


def print_results(results):
    """Print every available result and KPI of the results object.

    Run :func:`oemof.eesyplan.postprocessing.KPIs.calculate_all_kpis` first
    to fill the KPI namespace ``results["eesyplan"]``.
    """
    _print_result_structure(results)
    _print_kpis(results)
    _print_flows(results)
    _print_storages(results)
    _print_investments(results)
    _print_costs(results)
    _print_kpi_tables(results)


def _stored_kpis(results):
    """Return the KPI dictionary stored under ``results["eesyplan"]``."""
    try:
        return results[EESYPLAN_KEY]
    except Exception:
        data = getattr(results, "_data", None)
        if data is not None:
            return data.get(EESYPLAN_KEY, {})
        return getattr(results, EESYPLAN_KEY, {})


def _print_result_structure(results):
    """Print the structure of the imported results object."""
    print("=" * 78)
    print("RESULTS - STRUCTURE")
    print("=" * 78)
    print(f"type           : {type(results).__name__}")
    try:
        objective = f"{get_objective(results):.2f}"
    except ValueError:
        objective = "not available"
    print(f"objective      : {objective}")
    solver = _solver_value(results, "solver")
    if solver is not None:
        status = _solver_value(results, "termination_condition")
        print(f"solver         : {solver} ({status})")
    timeindex = getattr(results, "timeindex", None)
    if timeindex is None:
        print("timesteps      : not available")
    else:
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


def _print_kpis(results):
    """Print every scalar KPI stored in the results object."""
    kpis = _stored_kpis(results)
    print("KPIs:")
    printed = False
    for key, value in kpis.items():
        if isinstance(value, pd.DataFrame):
            continue
        printed = True
        if key == "lcoe_considered_flows":
            print(f"  {key}:")
            for source, target in value:
                print(f"    {source:>30} -> {target:<30}")
        elif isinstance(value, int | float):
            print(f"  {key:<30}: {value:,.6f}")
        else:
            print(f"  {key:<30}: {value}")
    if not printed:
        print("  none calculated (run calculate_all_kpis first)")
    print()


def _print_flows(results):
    """Print every connection (edge) of the flow time series."""
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


def _print_storages(results):
    """Print every storage in the storage_content time series."""
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


def _print_investments(results):
    """Print the optimized capacities (invest) and their costs."""
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


def _print_costs(results):
    """Print the variable costs per connection."""
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


def _print_cost_table(table, value_columns=None, title=""):
    """Print a cost table with a total column."""
    if value_columns is None:
        value_columns = [
            column
            for column in table.columns
            if column not in ("component", "total")
        ]
    component_width = max(
        26, max(len(str(value)) for value in table["component"]) + 2
    )
    width = max(20, max(len(column) for column in value_columns) + 2)
    if title:
        print(title)
    header = f"  {'component':<{component_width}}" + "".join(
        f"{column:>{width}}" for column in value_columns
    )
    print(header + f"{'total':>{width}}")
    print("  " + "-" * (component_width + width * (len(value_columns) + 1)))
    for _, row in table.iterrows():
        line = f"  {row['component']:<{component_width}}" + "".join(
            f"{row[column]:>{width},.2f}".replace(",", " ")
            for column in value_columns
        )
        total_str = f"{row['total']:>{width},.2f}".replace(",", " ")
        print(line + total_str)
    print()


def _print_kpi_tables(results):
    """Print the cost tables stored in the results object."""
    kpis = _stored_kpis(results)
    if "yearly_project_costs" in kpis:
        _print_cost_table(
            kpis["yearly_project_costs"], title="Yearly project costs:"
        )
    if "project_cost_table" in kpis:
        _print_cost_table(kpis["project_cost_table"], title="Project costs:")
