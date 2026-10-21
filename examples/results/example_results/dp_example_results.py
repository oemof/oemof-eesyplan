import argparse
import tkinter as tk
import warnings
from pathlib import Path
from tkinter import filedialog

from oemof.datapackage import datapackage  # noqa
from oemof.tools.debugging import ExperimentalFeatureWarning
from oemof.tools.logger import define_logging

from oemof.eesyplan import export_results  # noqa: F401
from oemof.eesyplan import import_results
from oemof.eesyplan.datapackage.energy_system import (
    create_energy_system_from_dp,
)
from oemof.eesyplan.model import optimise  # noqa: F401
from oemof.eesyplan.postprocessing import balance
from oemof.eesyplan.postprocessing import graphs
from oemof.eesyplan.postprocessing.KPIs import LCOE
from oemof.eesyplan.postprocessing.KPIs import clean_label
from oemof.eesyplan.postprocessing.KPIs import demand_labels
from oemof.eesyplan.postprocessing.KPIs import describe_results
from oemof.eesyplan.postprocessing.KPIs import normalize_imported_results
from oemof.eesyplan.postprocessing.KPIs import print_cost_table
from oemof.eesyplan.postprocessing.KPIs import print_costs
from oemof.eesyplan.postprocessing.KPIs import print_flows
from oemof.eesyplan.postprocessing.KPIs import print_investments
from oemof.eesyplan.postprocessing.KPIs import print_storages
from oemof.eesyplan.postprocessing.KPIs import project_cost_table
from oemof.eesyplan.postprocessing.KPIs import renewable_share
from oemof.eesyplan.postprocessing.KPIs import result_keys
from oemof.eesyplan.postprocessing.KPIs import yearly_project_costs

warnings.filterwarnings("ignore", category=ExperimentalFeatureWarning)


def file_dialog():
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

    es = create_energy_system_from_dp(Path(Path(__file__).parent / "scenario_Optimization_with_CHP"))
    #results = optimise(es)
    #export_results(results, path=Path(__file__).parent)
    imported_results = import_results(path=Path(__file__).parent, es=es)
    normalize_imported_results(imported_results)

    # --- 1. show how the whole object is built -------------------------------
    describe_results(imported_results)

    # --- 2. the existing checks ----------------------------------------------
    print(balance.nodes_io(imported_results["flow"]))
    fig, df = graphs.sankey(imported_results["flow"])
    fig.show()
    fig = graphs.plot_timeseries(imported_results, es)
    fig.show()
    fig = graphs.plot_energy_mix(imported_results, es)
    fig.show()

    # --- 3. walk through the object key by key -------------------------------
    #     keys()            -> all keys (set)
    #     result_keys(...)  -> without empty Problem/Solution/Solver
    #     results[key]      -> float for "objective", DataFrame otherwise
    #     results.timeindex -> shared DatetimeIndex of all time series
    print("Keys:", sorted(imported_results.keys()))
    print("Data keys:", result_keys(imported_results))
    print("Objective:", imported_results["objective"])
    print(f"Demand nodes: {sorted(demand_labels(es))}")
    lcoe, demand_flows = LCOE(imported_results, es)
    print(f"LCOE: {lcoe:.6f} EUR/kWh")
    print("Flows considered for the LCOE:")
    for source, target in demand_flows:
        print(f"  {clean_label(source):>30} -> {clean_label(target):<30}")
    print(f"Renewable share: {renewable_share(imported_results, es):.4f}")

    # --- 4. per-key loops ----------------------------------------------------
    print_flows(imported_results)
    print_storages(imported_results)
    print_investments(imported_results)
    print_costs(imported_results)

    # --- 4b. yearly project costs per component ------------------------------
    costs_table = yearly_project_costs(imported_results, es)
    print_cost_table(
        costs_table,
        [
            "annualized investment cost",
            "fix operational costs",
            "dispatch costs",
        ],
        "Yearly project costs:",
    )

    # --- 4c. total project costs over the project duration -------------------
    project_table = project_cost_table(imported_results, es)
    print_cost_table(
        project_table,
        [
            "investment cost in year 0 (not including reinvestment)",
            "fix operational costs over project duration",
            "dispatch costs over project duration",
        ],
        "Project costs (whole project duration):",
    )

    # --- 5. one-line access examples -----------------------------------------
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
