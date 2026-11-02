import argparse
import warnings
from pathlib import Path

from oemof.datapackage import datapackage  # noqa
from oemof.eesyplan import ThermalStorage
from oemof.eesyplan import export_results
from oemof.eesyplan import import_results
from oemof.eesyplan.datapackage.energy_system import (
    create_energy_system_from_dp,
)
from oemof.eesyplan.model import optimise
from oemof.eesyplan.postprocessing import balance
from oemof.eesyplan.postprocessing import graphs
from oemof.eesyplan.postprocessing.KPIs import calculate_all_kpis
from oemof.eesyplan.postprocessing.KPIs import demand_labels
from oemof.eesyplan.postprocessing.KPIs import normalize_imported_results
from oemof.eesyplan.postprocessing.KPIs import result_keys
from oemof.eesyplan.postprocessing.print_results import print_results
from oemof.tools.debugging import ExperimentalFeatureWarning
from oemof.tools.logger import define_logging

warnings.filterwarnings("ignore", category=ExperimentalFeatureWarning)

# The scenario datapackage keeps the older parameter names of the thermal
# storage. They are renamed here, the datapackage itself stays unchanged.
LEGACY_NAMES = {
    ThermalStorage: {
        "thermal_losses_variable": "loss_rate",
        "thermal_losses_fixed": "fixed_losses_relative",
    },
}


def file_dialog():
    import tkinter as tk  # noqa: PLC0415  (only needed for the dialog)
    from tkinter import filedialog  # noqa: PLC0415

    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(
        filetypes=[("Supported files", "*.json *.zip")]
    )


if __name__ == "__main__":
    define_logging()
    parser = argparse.ArgumentParser(
        prog="solve datapackage",
        description="Simulate an energy system from a datapackage",
    )
    parser.add_argument("-f", "--filename", default=None, type=str)
    parser.add_argument("-p", "--plot", default="graph", type=str)

    scenario_path = Path(__file__).parent / "scenario_Luft-Wärmepumpe_und_PV"
    results_path = scenario_path / "datapackage_solved"
    if (results_path / "datapackage.json").exists():
        es = create_energy_system_from_dp(
            scenario_path, attributemap=LEGACY_NAMES
        )
        imported_results = import_results(path=results_path, es=es)
    else:
        es = create_energy_system_from_dp(
            scenario_path, attributemap=LEGACY_NAMES
        )
        results = optimise(es)
        export_results(results, path=results_path)
        imported_results = import_results(path=results_path, es=es)

    normalize_imported_results(imported_results)
    calculate_all_kpis(imported_results, es)

    # --- 1. show how the whole object is built -------------------------------
    print_results(imported_results)

    # --- 2. the existing checks ----------------------------------------------
    print(balance.nodes_io(imported_results["flow"]))
    fig, df = graphs.sankey_2(imported_results, es, collapse_fascades=True)
    fig.show()
    fig = graphs.plot_timeseries(imported_results, es)
    fig.show()
    fig = graphs.plot_energy_mix(imported_results, es)
    fig.show()
    fig = graphs.plot_renewable_vs_nonrenewable(imported_results, es)
    fig.show()
    fig = graphs.capacities(imported_results, es)
    fig.show()
    fig = graphs.plot_annual_costs(imported_results, es)
    fig.show()

    # --- 3. access individual results and KPIs -------------------------------
    #     results[key]        -> DataFrame
    #     results.solver      -> solver summary (incl. the objective)
    #     results["eesyplan"] -> all calculated KPIs
    #     results.timeindex   -> shared DatetimeIndex of all time series
    print("Keys:", sorted(imported_results.keys()))
    print("Data keys:", result_keys(imported_results))
    print("KPI keys:", sorted(imported_results["eesyplan"]))
    print(f"Total cost: {imported_results['eesyplan']['total_cost']:.2f}")
    print(f"LCOE: {imported_results['eesyplan']['lcoe']:.6f} EUR/kWh")
    print(
        "Renewable share: "
        f"{imported_results['eesyplan']['renewable_share']:.4f}"
    )
    print(f"Demand nodes: {sorted(demand_labels(es))}")
    print("Flows considered for the LCOE:")
    for source, target in imported_results["eesyplan"][
        "lcoe_considered_flows"
    ]:
        print(f"  {source:>30} -> {target:<30}")

    # The cost tables are already printed by print_results:
    #   imported_results["eesyplan"]["yearly_project_costs"]
    #   imported_results["eesyplan"]["project_cost_table"]

    # --- 4. one-line access examples -----------------------------------------
    # one edge as a time series:
    #   col = next(c for c in imported_results["flow"].columns
    #              if edge_label(c) == ("PV-Dachanlage", "Strom_bus"))
    #   imported_results["flow"][col]
    # all edges as (from, to) pairs:
    #   [edge_label(c) for c in imported_results["flow"].columns]
    # peak of every edge:
    #   imported_results["flow"].max()
    # tidy long format of all flows (time, from, to):
    #   imported_results["flow"].stack([0, 1])
    # all values of a storage:
    #   imported_results["storage_content"][some_column].tolist()
