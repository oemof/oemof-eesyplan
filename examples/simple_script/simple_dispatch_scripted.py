from pathlib import Path

import pandas as pd

from oemof.eesyplan import CarrierBus
from oemof.eesyplan import Demand
from oemof.eesyplan import DsoElectricity
from oemof.eesyplan import ElectricalStorage
from oemof.eesyplan import Project
from oemof.eesyplan import PvPlant
from oemof.eesyplan import WindTurbine
from oemof.eesyplan import EnergySystem
from oemof.eesyplan import optimise

DATA_PATH = Path("data")

DATA_FILES = {
    "pv": Path("pv_profile.csv"),
    "demand_heat": Path("heat_demand.csv"),
    "wind": Path("wind_profile.csv"),
    "demand_elec": Path("electricity_demand.csv"),
}


def process_results(results):
    rdf = results["flow"]

    for n, m in [(0, 1), (1, 0)]:
        rdf.rename(
            columns={
                c[n]: c[n].label[-1]
                for c in rdf.columns
                if isinstance(c[n].label, tuple)
                and not isinstance(c[m].label, tuple)
            },
            level=n,
            inplace=True,
        )
    elec_in = rdf[[c for c in rdf.columns if c[0] == "electricity"]]
    elec_out = rdf[[c for c in rdf.columns if c[1] == "electricity"]]
    print(elec_in.sum())
    print(elec_out.sum())
    print("*****************")
    print("Input:", round(elec_in.sum().sum()))
    print("Output:", round(elec_out.sum().sum()))
    if "invest" in results:
        print("Invest:", results["invest"])

    print("Objective:", results["objective"])


def simple_script():
    # Read data file
    project = Project(name="test", lifetime=20, tax=0, discount_factor=0)

    data = {}
    for key, fn in DATA_FILES.items():
        path = Path(DATA_PATH, fn)
        data[key] = pd.read_csv(path, header=None).squeeze()

    # ####################### initialize the energy system ####################
    energy_system = EnergySystem(2023)

    # ######################### create energysystem components ################

    # carrier
    bus_elec = CarrierBus(name="electricity")

    energy_system.add(bus_elec)

    energy_system.add(
        DsoElectricity(
            name="My_DSO",
            bus_electricity=bus_elec,
            energy_price=0.1,
            feedin_tariff=0.04,
        )
    )

    # sources
    energy_system.add(
        WindTurbine(
            name="wind",
            bus_out_electricity=bus_elec,
            input_timeseries=data["wind"],
            installed_capacity=6.63,
            project_data=project,
            optimize_cap=False,
        )
    )

    energy_system.add(
        PvPlant(
            name="pv",
            bus_out_electricity=bus_elec,
            project_data=project,
            installed_capacity=5.0,
            input_timeseries=data["pv"],
            optimize_cap=False,
        )
    )

    energy_system.add(
        ElectricalStorage(
            name="Batterie",
            bus_in_electricity=bus_elec,
            age_installed=0,
            installed_capacity=1000,
            capex_var=3.0,
            opex_fix=5.0,
            opex_var=0.0,
            lifetime=10.0,
            optimize_cap=False,
            soc_max=1,
            soc_min=0,
            crate=1.0,
            efficiency=0.99,
            project_data=project,
            self_discharge=0.000,
        )
    )

    # demands (electricity/heat)
    energy_system.add(
        Demand(
            name="demand_el",
            bus_in_electricity=bus_elec,
            input_timeseries=data["demand_elec"],
        )
    )
    return optimise(energy_system)


if __name__ == "__main__":
    results = simple_script()
    process_results(results)
