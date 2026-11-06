from numpy.typing import ArrayLike

from oemof.eesyplan.type_checks import normalise
from oemof.network import Node
from oemof.solph import Bus
from oemof.solph import Flow
from oemof.solph import Investment
from oemof.solph.components import Sink
from oemof.solph.components import Source


class DSO(Node):
    """
    Distribution system operator for grid energy exchange.

    This component models a distribution system operator (DSO) that
    supplies energy to a bus and optionally absorbs energy from it. Energy
    supplied to the bus is priced with the energy price, and absorbed
    energy is credited with the feedin tariff. A basic amount can be added
    as a fixed cost.

    .. important::
        At least one of energy_price and feedin_tariff must be set. Setting
        a maximum_feedin_capacity without a feedin_tariff raises a
        ValueError.

    Args:
        name: |name|
        bus: |bus|
        energy_price: (optional) -- |energy_price|
        feedin_tariff: (optional) -- |feedin_tariff|
        maximum_capacity: (optional) -- |maximum_capacity|
        maximum_feedin_capacity: (optional) -- |maximum_feedin_capacity|
        peak_demand_pricing: (optional) -- |peak_demand_pricing|
        basic_amount: (optional) -- |basic_amount|

    Examples:
        >>> from oemof.eesyplan import CarrierBus
        >>> ebus = CarrierBus(name="any_bus")
        >>> my_dso = DSO(
        ...     name="any_network",
        ...     bus=ebus,
        ...     energy_price=0.25,
        ...     )
        >>> feedin_dso = DSO(
        ...     name="any_network",
        ...     bus=ebus,
        ...     feedin_tariff=0.15,
        ...     )
    """

    def __init__(
        self,
        name: str,
        bus: Bus,
        energy_price: float | int | ArrayLike | None = None,
        feedin_tariff: float | int | ArrayLike | None = None,
        maximum_capacity: float | int | None = None,
        maximum_feedin_capacity: float | int | None = None,
        peak_demand_pricing: float | int = 0,
        basic_amount=0,  # Warnung, weil nur für Profis :-)
    ):
        self.name = name
        self.bus = bus
        self.maximum_capacity = normalise(maximum_capacity)
        self.maximum_feedin_capacity = normalise(maximum_feedin_capacity)
        self.energy_price = normalise(energy_price)
        self.feedin_tariff = normalise(feedin_tariff)
        self.peak_demand_pricing = normalise(peak_demand_pricing)
        self.fix_cost = normalise(basic_amount)

        super().__init__(label=self.name)

        if energy_price is None and feedin_tariff is None:
            raise ValueError(
                "Either energy_price or feedin_tariff must be set"
            )

        if self.feedin_tariff is not None:
            if self.maximum_feedin_capacity is not None:
                nominal_capacity = self.maximum_feedin_capacity
            else:
                nominal_capacity = self.maximum_capacity

            self.subnode(
                Sink,
                inputs={
                    self.bus: Flow(
                        variable_costs=self.feedin_tariff * -1,
                        nominal_capacity=nominal_capacity,
                    )
                },
                local_name="feedin_sink",
            )
        else:
            if self.maximum_feedin_capacity is not None:
                raise ValueError(
                    f"The maximum_feedin_capacity is "
                    f"{self.maximum_feedin_capacity} but no feedin_tariff is "
                    f"defined."
                )

        if energy_price is not None:
            if self.maximum_capacity is None:
                maximum = float("inf")
            else:
                maximum = self.maximum_capacity
            self.subnode(
                Source,
                outputs={
                    self.bus: Flow(
                        variable_costs=self.energy_price,
                        nominal_capacity=Investment(
                            ep_costs=self.peak_demand_pricing,
                            maximum=maximum,
                        ),
                    )
                },
                local_name="consumption_source",
            )
