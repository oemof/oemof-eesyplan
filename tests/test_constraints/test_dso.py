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
