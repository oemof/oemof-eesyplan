import numpy as np
import pytest

from oemof.eesyplan import CarrierBus as Bus
from oemof.eesyplan import ChpFixedRatio
from oemof.eesyplan import ChpVariableRatio
from oemof.eesyplan import EnergySystem
from oemof.eesyplan import Project
from oemof.eesyplan import optimise

NUMBER = 10


@pytest.fixture
def buses():
    gas_bus = Bus(name="gas_bus", balanced=False)
    heat_bus = Bus(name="heat_bus", balanced=False)
    el_bus = Bus(name="electricity_bus", balanced=False)
    return gas_bus, heat_bus, el_bus


@pytest.fixture
def project():
    return Project(
        name="Project_X",
        economic_period=20,
        tax=0,
        discount_factor=0.01,
    )


def build_energy_system(buses):
    gas_bus, heat_bus, el_bus = buses
    es = EnergySystem(2023, number=NUMBER)
    es.add(gas_bus, heat_bus, el_bus)
    return es


def build_chp_fixed(buses, project, installed, maximum):
    gas_bus, heat_bus, el_bus = buses
    return ChpFixedRatio(
        name="fixed_ratio_chp",
        bus_in_fuel=gas_bus,
        bus_out_heat=heat_bus,
        bus_out_electricity=el_bus,
        installed_capacity=installed,
        maximum_capacity=maximum,
        efficiency_electricity_chp=np.arange(-1, 0, 0.1) * -1,
        efficiency_heat_chp=np.arange(0, 1, 0.1),
        variable_costs=-1000,
        project_data=project,
    )


def build_chp_variable(buses, project, installed, maximum):
    gas_bus, heat_bus, el_bus = buses
    return ChpVariableRatio(
        name="fixed_ratio_chp",
        bus_in_fuel=gas_bus,
        bus_out_heat=heat_bus,
        bus_out_electricity=el_bus,
        installed_capacity=installed,
        maximum_capacity=maximum,
        efficiency_electricity_state_a=0.55,
        efficiency_heat_state_a=0,
        efficiency_electricity_state_b=0.32,
        efficiency_heat_state_b=0.58,
        variable_costs=-1000,
        project_data=project,
    )


# Two cases: Dispatch (300, None), Investment (None, 300)
@pytest.mark.parametrize(("installed", "maximum"), [(300, None), (None, 300)])
def test_chp_fixed(buses, project, installed, maximum):
    es = build_energy_system(buses)
    gas_bus, heat_bus, el_bus = buses
    chp_fixed = build_chp_fixed(buses, project, installed, maximum)
    es.add(chp_fixed)

    results = optimise(es)
    flows = results["flow"]
    flow_sum = flows.sum()

    capacity = installed or maximum
    energy = capacity * NUMBER

    assert flow_sum[chp_fixed, el_bus] == energy
    assert flow_sum[chp_fixed, heat_bus] == pytest.approx(
        (
            flows[chp_fixed, el_bus]
            / (np.arange(-1, 0, 0.1) * -1)
            * np.arange(0, 1, 0.1)
        ).sum(),
        0.000000001,
    )
    assert (flow_sum[chp_fixed, heat_bus] + energy) == pytest.approx(
        flow_sum[gas_bus, chp_fixed], 0.000000001
    )


# Two cases: Dispatch (300, None), Investment (None, 300)
@pytest.mark.parametrize(("installed", "maximum"), [(300, None), (None, 300)])
def test_chp_variable(buses, project, installed, maximum):
    es = build_energy_system(buses)
    gas_bus, heat_bus, el_bus = buses
    chp_var = build_chp_variable(buses, project, installed, maximum)
    es.add(chp_var)

    results = optimise(es)
    flows = results["flow"]
    flow_sum = flows.sum()

    capacity = installed or maximum
    energy = capacity * NUMBER

    assert flow_sum[chp_var, el_bus] == energy
    assert flow_sum[chp_var, heat_bus] == 0
    assert flow_sum[chp_var, el_bus] / (
        chp_var.efficiency_electricity_state_a
    ) == pytest.approx(flow_sum[gas_bus, chp_var], 0.00001)
