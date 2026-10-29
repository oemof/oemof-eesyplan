import pytest

from oemof.eesyplan import CarrierBus
from oemof.eesyplan import FlowPricing


def test_pricing_error():
    bus_in = CarrierBus(name="bus_in")
    bus_out = CarrierBus(name="bus_out")
    msg = "full_load_time_limit cannot be set to infinity"
    with pytest.raises(ValueError, match=msg):
        FlowPricing(
            name="extra_pricing_node",
            bus_in=bus_in,
            bus_out=bus_out,
            cost_unlimited=0.1,
            cost_limited=0.2,
            maximum_capacity=None,
            full_load_time_limit=3000,
        )
