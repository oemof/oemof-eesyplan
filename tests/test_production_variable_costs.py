import pytest

from oemof.eesyplan import BiogasPlant
from oemof.eesyplan import CarrierBus
from oemof.eesyplan import GeothermalPlant
from oemof.eesyplan import Project
from oemof.eesyplan import PvPlant
from oemof.eesyplan import SolarThermalPlant
from oemof.eesyplan import WindTurbine

PLANTS = [
    pytest.param(WindTurbine, "bus_out_electricity", id="wind"),
    pytest.param(PvPlant, "bus_out_electricity", id="pv"),
    pytest.param(SolarThermalPlant, "bus_out_heat", id="solar_thermal"),
    pytest.param(GeothermalPlant, "bus_out_heat", id="geothermal"),
    pytest.param(BiogasPlant, "bus_out_fuel", id="biogas"),
]


@pytest.mark.parametrize(("plant_class", "bus_keyword"), PLANTS)
def test_passes_variable_costs_to_output_flow(plant_class, bus_keyword):
    project = Project(
        name="test", economic_period=20, tax=0, discount_factor=0
    )
    bus = CarrierBus(name="test_bus")
    plant = plant_class(
        project_data=project,
        name="test_plant",
        input_timeseries=[1, 2, 3],
        variable_costs=-0.01,
        **{bus_keyword: bus},
    )

    flow = next(iter(plant.outputs.values()))

    assert flow.variable_costs[0] == -0.01
