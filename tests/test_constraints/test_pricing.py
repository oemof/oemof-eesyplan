import numpy as np
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
            virtual_flow_capacity=None,
            full_load_time_limit=3000,
        )


@pytest.mark.parametrize("limit", [[1000, 2000], np.array([1000, 2000])])
def test_pricing_non_scalar_full_load_time_limit(limit):
    bus_in = CarrierBus(name="bus_in")
    bus_out = CarrierBus(name="bus_out")
    with pytest.raises(ValueError, match="must be a scalar"):
        FlowPricing(
            name="extra_pricing_node",
            bus_in=bus_in,
            bus_out=bus_out,
            cost_unlimited=0.1,
            cost_limited=0.2,
            virtual_flow_capacity=500,
            full_load_time_limit=limit,
        )
