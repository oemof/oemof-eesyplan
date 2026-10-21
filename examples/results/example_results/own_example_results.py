import argparse
import logging
import warnings
from pathlib import Path

import pandas as pd

from oemof.datapackage import datapackage  # noqa
from oemof.eesyplan import CarrierBus
from oemof.eesyplan import ChpFixedRatio
from oemof.eesyplan import Commodity
from oemof.eesyplan import ElectricalStorage
from oemof.eesyplan import ElectricityDemand
from oemof.eesyplan import Excess
from oemof.eesyplan import FuelStorage
from oemof.eesyplan import HeatDemand
from oemof.eesyplan import Project
from oemof.eesyplan import PvPlant
from oemof.eesyplan import ThermalStorage
from oemof.eesyplan import WindTurbine
from oemof.eesyplan import export_results
from oemof.eesyplan import import_results
from oemof.eesyplan.model import optimise
from oemof.eesyplan.postprocessing import graphs
from oemof.eesyplan.postprocessing.KPIs import calculate_all_kpis
from oemof.eesyplan.postprocessing.KPIs import normalize_imported_results
from oemof.eesyplan.postprocessing.print_results import print_results
from oemof.solph import EnergySystem
from oemof.solph import Model
from oemof.solph import Results
from oemof.solph import create_time_index
from oemof.tools import logger
from oemof.tools.debugging import ExperimentalFeatureWarning
from oemof.tools.logger import define_logging

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
            variable_costs=0.1,
        )
    )

    # eesyplan has no investable generic source facade, so the waste heat
    # source is modelled as an unlimited commodity.
    energysystem.add(
        Commodity(
            name="waste_heat",
            bus_out=bus_heat,
            commodity="waste_heat",
            variable_costs=0.01,
        )
    )

    energysystem.add(
        WindTurbine(
            name="wind",
            bus_out_electricity=bus_electricity,
            input_timeseries=data["wind"],
            project_data=project,
            capex_spec=1100,
            opex_spec=10,
            variable_costs=-0.01,
            lifetime=20,
            installed_capacity=300000,
            age_installed=15,
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
            age_installed=10,
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

    energysystem.add(Excess(name="sold", bus_in=bus_electricity, cost=-0.1))

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

    scenario_path = Path(__file__).parent / "scenario_own_example"
    results_path = scenario_path / "datapackage_solved"
    es = create_energysystem()
    results = optimise(es)
    export_results(results, path=results_path)
    imported_results = import_results(path=results_path, es=es)
    normalize_imported_results(imported_results)
    calculate_all_kpis(imported_results, es)

    # --- 1. show how the whole object is built -------------------------------
    print_results(imported_results)

    # --- 2. the existing checks ----------------------------------------------
    fig, df = graphs.sankey_2(imported_results, es)
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
