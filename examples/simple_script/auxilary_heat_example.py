from pathlib import Path

import pandas as pd

from oemof.eesyplan import CarrierBus, AuxiliaryHeat
from oemof.eesyplan import EnergySystem
from oemof.eesyplan import Project
from oemof.eesyplan import SolarThermalPlant
from oemof.eesyplan import HeatDemand
from oemof.eesyplan import optimise
from oemof.eesyplan.postprocessing.graphs import sankey
from oemof.tools.logger import define_logging

DATA_PATH = Path("data")

DATA_FILES = {
    "demand_heat": Path("heat_demand.csv"),
}


def simple_script():
    # Read data file
    data = {}
    for key, fn in DATA_FILES.items():
        path = Path(DATA_PATH, fn)
        data[key] = pd.read_csv(path, header=None).squeeze()

    project = Project(
        name="test", economic_period=20, tax=0, discount_factor=0
    )

    # ####################### initialize the energy system ####################
    energy_system = EnergySystem(2023, number=180)

    # ######################### create energysystem components ################

    # carrier
    bus_heat_source = CarrierBus(name="heat_source",excess_cost=1) #available heat which does not always have the neccecary temperature
    bus_heat_aux = CarrierBus(name="heat_aux",excess_cost=1) #available high temperature heat to overheat
    bus_heat_out = CarrierBus(name="heat_out",excess_cost=1) #output of the auxilary_heater

    energy_system.add(bus_heat_source,bus_heat_aux,bus_heat_out)

    # sources
    energy_system.add(
        SolarThermalPlant(
            name="low_T_source",
            bus_out_heat=bus_heat_source,
            input_timeseries=1,
            installed_capacity=10,
            project_data=project,
        )
    )

    energy_system.add(
        SolarThermalPlant(
            name="high_T_source",
            bus_out_heat=bus_heat_aux,
            project_data=project,
            installed_capacity=100.0,
            input_timeseries=1,
        )
    )

    energy_system.add(
        AuxiliaryHeat(
            name="auxilary_mixer",
            bus_in_heat=bus_heat_source,
            bus_in_heat_auxiliary=bus_heat_aux,
            bus_out_heat=bus_heat_out,
            temp_in_heat=data["demand_heat"]/max(data["demand_heat"])*40+20,
            temp_out_heat=data["demand_heat"]/max(data["demand_heat"])*40+60, #T between 60-100°C
            temp_low_source_component=60,
            project_data=project,
            installed_capacity=10,
        )
    )

    # demands (electricity/heat)
    energy_system.add(
        HeatDemand(
            name="demand_heat",
            bus_in_heat=bus_heat_out,
            input_timeseries=1,
        )
    )

    return optimise(energy_system), energy_system


if __name__ == "__main__":
    define_logging()
    res, es = simple_script()

    fig,pd = sankey(res["flow"], es=es)
    fig.show()

