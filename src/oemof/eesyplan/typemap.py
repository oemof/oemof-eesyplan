from oemof.eesyplan import CHP
from oemof.eesyplan import Battery
from oemof.eesyplan import BiogasPlant
from oemof.eesyplan import Boiler
from oemof.eesyplan import CarrierBus
from oemof.eesyplan import ChpFixedRatio
from oemof.eesyplan import ChpVariableRatio
from oemof.eesyplan import Demand
from oemof.eesyplan import DieselGenerator
from oemof.eesyplan import DsoElectricity
from oemof.eesyplan import DsoFuel
from oemof.eesyplan import DsoHeat
from oemof.eesyplan import DsoHydrogen
from oemof.eesyplan import ElectricalStorage
from oemof.eesyplan import ElectricalTransformator
from oemof.eesyplan import Electrolyzer
from oemof.eesyplan import FuelCell
from oemof.eesyplan import FuelDemand
from oemof.eesyplan import FuelStorage
from oemof.eesyplan import GeothermalPlant
from oemof.eesyplan import H2Demand
from oemof.eesyplan import HeatDemand
from oemof.eesyplan import HeatPump
from oemof.eesyplan import HydrogenStorage
from oemof.eesyplan import Project
from oemof.eesyplan import PvPlant
from oemof.eesyplan import SolarThermalPlant
from oemof.eesyplan import ThermalStorage
from oemof.eesyplan import WindTurbine
from oemof.solph.components import Source

TYPEMAP = {
    "CHP": CHP,
    "Battery": Battery,
    "CarrierBus": CarrierBus,
    "demand": Demand,
    "Source": Source,
    "project": Project,
    "pv_plant": PvPlant,
    "wind_plant": WindTurbine,
    "dso_electricity": DsoElectricity,
    "dso": DsoElectricity,
    "gas_dso": DsoFuel,
    "h2_dso": DsoHydrogen,
    "heat_dso": DsoHeat,
    "gas_demand": FuelDemand,
    "h2_demand": H2Demand,
    "heat_demand": HeatDemand,
    "transformer_station_in": ElectricalTransformator,
    "transformer_station_out": ElectricalTransformator,
    "storage_charge_controller_in": ElectricalTransformator,
    "storage_charge_controller_out": ElectricalTransformator,
    "solar_inverter": ElectricalTransformator,
    "diesel_generator": DieselGenerator,
    "fuel_cell": FuelCell,
    "gas_boiler": Boiler,
    "electrolyzer": Electrolyzer,
    "heat_pump": HeatPump,
    "biogas_plant": BiogasPlant,
    "geothermal_conversion": GeothermalPlant,
    "solar_thermal_plant": SolarThermalPlant,
    "bess": ElectricalStorage,
    "gess": FuelStorage,
    "h2ess": HydrogenStorage,
    "hess": ThermalStorage,
    "chp": ChpVariableRatio,
    "chp_fixed_ratio": ChpFixedRatio,
}
