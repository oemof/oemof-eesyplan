import pytest

from oemof.eesyplan import DSO
from oemof.eesyplan import CarrierBus


def test_dso_without_costs():
    ebus = CarrierBus(name="any_bus")
    msg = "Either energy_price or feedin_tariff must be set"
    with pytest.raises(ValueError, match=msg):
        DSO(
            name="any_network",
            bus=ebus,
        )


def test_dso_feedin_capacity_without_feedin_tariff():
    ebus = CarrierBus(name="any_bus")
    with pytest.raises(ValueError, match="no feedin_tariff is defined"):
        DSO(
            name="any_network",
            bus=ebus,
            energy_price=0.25,
            maximum_feedin_capacity=10,
        )


def test_dso_feedin_uses_maximum_feedin_capacity():
    ebus = CarrierBus(name="any_bus")
    dso = DSO(
        name="any_network",
        bus=ebus,
        feedin_tariff=0.1,
        maximum_capacity=100,
        maximum_feedin_capacity=50,
    )
    assert dso.maximum_feedin_capacity == 50.0
    assert dso.maximum_capacity == 100.0
    assert len(dso.subnodes) == 1
