import logging
from pathlib import Path

import oemof.solph
import pandas as pd
from oemof.solph import EnergySystem
from oemof.solph import Model
from oemof.solph import Results
from oemof.solph import buses
from oemof.solph import components
from oemof.solph import create_time_index
from oemof.solph import flows
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
from oemof.eesyplan import Demand
from oemof.eesyplan import FuelDemand
from oemof.eesyplan import H2Demand
from oemof.eesyplan import HeatDemand
from oemof.eesyplan import export_results
from oemof.eesyplan import import_results
from oemof.solph.components import Source
from oemof.eesyplan.datapackage.energy_system import (
    create_energy_system_from_dp,
)
from oemof.eesyplan.datapackage.energy_system import unzip_package
from oemof.eesyplan.model import optimise
from oemof.eesyplan.postprocessing import balance
from oemof.tools.debugging import ExperimentalFeatureWarning
from oemof.tools.logger import define_logging
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

    bus_gas = buses.Bus(label="natural_gas")
    bus_electricity = buses.Bus(label="electricity")
    bus_heat = buses.Bus(label="bus_heat")

    energysystem.add(bus_gas, bus_electricity, bus_heat)

    energysystem.add(
        components.Source(
            label="rgas",
            outputs={bus_gas: flows.Flow(variable_costs=0.1)},
        )
    )

    energysystem.add(
        components.Source(
            label="waste_heat",
            outputs={bus_heat: flows.Flow(
                nominal_capacity=oemof.solph.Investment(
                    ep_costs=300 / 12),
                variable_costs=0.01)},
        )
    )

    energysystem.add(
        components.Source(
            label="wind",
            outputs={
                bus_electricity: flows.Flow(
                    max=data["wind"],
                    nominal_capacity=oemof.solph.Investment(
                        ep_costs=1100 / 12
                    ),
                    variable_costs=0.001,
                )
            },
        )
    )

    energysystem.add(
        components.Source(
            label="pv",
            outputs={
                bus_electricity: flows.Flow(
                    max=data["pv"],
                    nominal_capacity=oemof.solph.Investment(ep_costs=600/20/12,maximum=1000000),
                    variable_costs=0.001,
                )
            },
        )
    )

    energysystem.add(
        components.Sink(
            label="demand_el",
            inputs={
                bus_electricity: flows.Flow(
                    fix=data["demand_el"], nominal_capacity=1
                )
            },
        )
    )

    energysystem.add(
        components.Sink(
            label="demand_heat",
            inputs={
                bus_heat: flows.Flow(
                    fix=data["demand_heat"], nominal_capacity=0.4
                )
            },
        )
    )

    energysystem.add(
        components.Sink(
            label="heat_excess",
            inputs={bus_heat: flows.Flow()},
        )
    )

    energysystem.add(
        components.Sink(
            label="sold",
            inputs={bus_electricity: flows.Flow(variable_costs=-0.1)},
        )
    )

    energysystem.add(
        components.Converter(
            label="pp_gas",
            inputs={bus_gas: flows.Flow()},
            outputs={
                bus_electricity: flows.Flow(
                    nominal_capacity=oemof.solph.Investment(ep_costs=600 / 12),
                    variable_costs=0.01,
                ),
                bus_heat: flows.Flow(),
            },
            conversion_factors={bus_electricity: 0.3, bus_heat: 0.5},
        )
    )

    energysystem.add(
        components.Converter(
            label="backwards",
            inputs={bus_heat: flows.Flow()},
            outputs={
                bus_gas: flows.Flow(
                    nominal_capacity=oemof.solph.Investment(
                        ep_costs=60 / 12, maximum=100
                    ),
                    variable_costs=10,
                )
            },
            conversion_factors={bus_gas: 1},
        )
    )

    nominal_capacity = oemof.solph.Investment(ep_costs=1 / 12, maximum=100)
    gas_storage = components.GenericStorage(
        nominal_capacity=nominal_capacity,
        label="gas_storage",
        inputs={bus_gas: flows.Flow()},
        outputs={
            bus_gas: flows.Flow(
                nominal_capacity=nominal_capacity, variable_costs=-1
            )
        },
        loss_rate=0.00,
        initial_storage_level=None,
        inflow_conversion_factor=1,
        outflow_conversion_factor=1,
    )
    energysystem.add(gas_storage)

    nominal_capacity = oemof.solph.Investment(ep_costs=10 / 12)
    battery_storage = components.GenericStorage(
        nominal_capacity=nominal_capacity,
        label="battery_storage",
        inputs={bus_electricity: flows.Flow()},
        outputs={
            bus_electricity: flows.Flow(
                nominal_capacity=nominal_capacity, variable_costs=0.001
            )
        },
        loss_rate=0.00,
        initial_storage_level=None,
        inflow_conversion_factor=1,
        outflow_conversion_factor=1,
    )
    energysystem.add(battery_storage)

    nominal_capacity = oemof.solph.Investment(ep_costs=1 / 12)
    heat_storage = components.GenericStorage(
        nominal_capacity=nominal_capacity,
        label="heat_storage",
        inputs={bus_heat: flows.Flow()},
        outputs={
            bus_heat: flows.Flow(
                nominal_capacity=nominal_capacity, variable_costs=0.001
            )
        },
        loss_rate=0.00,
        initial_storage_level=None,
        inflow_conversion_factor=1,
        outflow_conversion_factor=0.9,
    )
    energysystem.add(heat_storage)

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
    #es = create_energy_system_from_dp(Path(Path(__file__).parent / "scenario_Optimization_with_CHP"))
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
        ["capex", "opex", "variable_cost"],
        "Yearly project costs:",
    )

    # --- 4c. total project costs over the project duration -------------------
    project_table = project_cost_table(imported_results, es)
    print_cost_table(
        project_table,
        ["investment_cost", "operational_cost", "variable_cost"],
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


