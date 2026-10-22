import logging
from pathlib import Path

import pandas as pd
from oemof.solph import EnergySystem
from oemof.solph import Model
from oemof.solph import Results
from oemof.solph import create_time_index
from oemof.tools import logger

import argparse
import re
import tempfile
import tkinter as tk
import warnings
from pathlib import Path
from tkinter import filedialog

import pandas as pd

from oemof.datapackage import datapackage  # noqa
from oemof.eesyplan import CarrierBus
from oemof.eesyplan import ChpFixedRatio
from oemof.eesyplan import Commodity
from oemof.eesyplan import ElectricalStorage
from oemof.eesyplan import ElectricityDemand
from oemof.eesyplan import Excess
from oemof.eesyplan import export_results
from oemof.eesyplan import FuelStorage
from oemof.eesyplan import HeatDemand
from oemof.eesyplan import import_results
from oemof.eesyplan import Project
from oemof.eesyplan import PvPlant
from oemof.eesyplan import ThermalStorage
from oemof.eesyplan import WindTurbine
from oemof.eesyplan.datapackage.energy_system import (
    create_energy_system_from_dp,
)
from oemof.eesyplan.datapackage.energy_system import unzip_package
from oemof.eesyplan.model import optimise
from oemof.eesyplan.postprocessing import balance
from oemof.tools.debugging import ExperimentalFeatureWarning
from oemof.tools.logger import define_logging
from oemof.eesyplan.postprocessing import graphs
from oemof.eesyplan.postprocessing.graphs import capacities_graph

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

DATA_PATH = Path(__file__).parent


def get_data_from_file_path(file_path: str):
    try:
        data = pd.read_csv(file_path)
    except FileNotFoundError:
        data = pd.read_csv(Path(DATA_PATH, file_path))
    return data


def create_energysystem():
    file_name = "time_series_month.csv"
    data = get_data_from_file_path(file_name)

    number_of_time_steps = len(data)

    logging.info("Initialize the energy system")
    date_time_index = create_time_index(2012, number=number_of_time_steps)

    energysystem = EnergySystem(
        timeindex=date_time_index, infer_last_interval=False
    )

    project = Project(
        name="own_example",
        economic_period=20,
        tax=0,
        discount_factor=0.05,
    )

    bus_gas = CarrierBus(name="natural_gas", carrier="gas")
    bus_electricity = CarrierBus(name="electricity", carrier="electricity")
    bus_heat = CarrierBus(name="bus_heat", carrier="heat")

    energysystem.add(bus_gas, bus_electricity, bus_heat)

    energysystem.add(
        Commodity(
            name="rgas",
            bus_out=bus_gas,
            commodity="natural_gas",
            variable_cost=0.1,
        )
    )

    # eesyplan has no investable generic source facade, so the waste heat
    # source is modelled as an unlimited commodity.
    energysystem.add(
        Commodity(
            name="waste_heat",
            bus_out=bus_heat,
            commodity="waste_heat",
            variable_cost=0.01,
        )
    )

    energysystem.add(
        WindTurbine(
            name="wind",
            bus_out_electricity=bus_electricity,
            input_timeseries=data["wind"],
            project_data=project,
            capex_spec=1100,
            opex_spec=0,
            variable_costs=0.001,
            lifetime=20,
        )
    )

    energysystem.add(
        PvPlant(
            name="pv",
            bus_out_electricity=bus_electricity,
            input_timeseries=data["pv"],
            project_data=project,
            capex_spec=600,
            opex_spec=10,
            variable_costs=0.001,
            lifetime=15,
            installed_capacity=2,
            age_installed=1,
        )
    )

    energysystem.add(
        ElectricityDemand(
            name="demand_el",
            bus_in_electricity=bus_electricity,
            input_timeseries=data["demand_el"],
        )
    )

    energysystem.add(
        HeatDemand(
            name="demand_heat",
            bus_in_heat=bus_heat,
            input_timeseries=data["demand_heat"],
        )
    )

    energysystem.add(Excess(name="heat_excess", bus_in=bus_heat, cost=0))

    energysystem.add(
        Excess(name="sold", bus_in=bus_electricity, cost=-0.1)
    )

    energysystem.add(
        ChpFixedRatio(
            name="pp_gas",
            bus_in_fuel=bus_gas,
            bus_out_electricity=bus_electricity,
            bus_out_heat=bus_heat,
            efficiency_electricity_chp=0.3,
            efficiency_heat_chp=0.5,
            project_data=project,
            capex_spec=600,
            opex_spec=0,
            variable_costs=0.01,
            lifetime=20,
        )
    )

    energysystem.add(
        FuelStorage(
            name="gas_storage",
            project_data=project,
            bus_in_fuel=bus_gas,
            bus_out_fuel=bus_gas,
            capex_spec=1,
            opex_spec=0,
            variable_costs=0,
            lifetime=20,
            maximum_capacity=100,
        )
    )

    energysystem.add(
        ElectricalStorage(
            name="battery_storage",
            project_data=project,
            bus_in_electricity=bus_electricity,
            bus_out_electricity=bus_electricity,
            capex_spec=10,
            opex_spec=0,
            variable_costs=0.001,
            lifetime=20,
        )
    )

    energysystem.add(
        ThermalStorage(
            name="heat_storage",
            project_data=project,
            bus_in_heat=bus_heat,
            bus_out_heat=bus_heat,
            capex_spec=1,
            opex_spec=0,
            variable_costs=0.001,
            lifetime=20,
            efficiency_discharge=0.9,
        )
    )

    return energysystem


def optimize_energysystem(energysystem):
    logging.info("Optimise the energy system")

    energysystem_model = Model(energysystem)

    solver = "cbc"
    solver_verbose = False

    logger.define_logging(
        logfile="oemof_example.log",
        screen_level=logging.INFO,
        file_level=logging.INFO,
    )

    logging.info("Solve the optimization problem")
    energysystem_model.solve(
        solver=solver, solve_kwargs={"tee": solver_verbose}
    )

    logging.info("Store the energy system with the results.")

    results = Results(energysystem_model)
    print("Energy System Optimized")

    return results


if __name__ == "__main__":
    define_logging()
    parser = argparse.ArgumentParser(
        prog="solve datapackage",
        description="Simulate an energy system from a datapackage",
    )
    parser.add_argument("-f", "--filename", default=None, type=str)
    parser.add_argument("-p", "--plot", default="graph", type=str)

    es = create_energysystem()
    results = optimise(es)
    export_results(results, path=Path(__file__).parent)
    imported_results = import_results(path=Path(__file__).parent, es=es)
    normalize_imported_results(imported_results)

    # --- 1. show how the whole object is built -------------------------------
    describe_results(imported_results)

    # --- 2. the existing checks ----------------------------------------------
    print(balance.nodes_io(imported_results["flow"]))
    fig, df = graphs.sankey(imported_results["flow"])
    fig.show()

    fig2 = capacities_graph(results["invest"], es)
    fig2.show()

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
    print_cost_table(costs_table, title="Yearly project costs:")

    # --- 4c. total project costs over the project duration -------------------
    project_table = project_cost_table(imported_results, es)
    print_cost_table(project_table, title="Project costs:")

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



