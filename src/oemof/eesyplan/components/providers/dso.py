from numpy.typing import ArrayLike

from oemof.network import Node
from oemof.solph import Flow
from oemof.solph import Investment
from oemof.solph.components import Sink
from oemof.solph.components import Source


class DSO(Node):
    def __init__(
        self,
        name: str,
        bus: CarrierBus,
        energy_price: float | int | ArrayLike | None = None,
        feedin_tariff: float | int | ArrayLike | None = None,
        maximum_capacity: float | int | None = None,
        peak_demand_pricing: float | int = 0,
        # peak_demand_pricing_period=1, ToDo: Still important? Not used!
        basic_amount=0,  # Warnung, weil nur für Profis :-)
    ):
        """
        Generic energy provider for distribution.

        This class represents a distribution system operator (DSO) that
        provides energy from the utility grid with pricing and
        feedin capabilities.

        .. important ::
            The renewable share affects the overall system renewable
            factor calculation.

        Structure
        ---------
        *input* & *output*
            bus : Any

        Parameters
        ----------
        name : str
            |name|
        energy_price
            |energy_prices|
        feedin_tariff
            |feedin_tariff|
        peak_demand_pricing
            |peak_demand_pricing|
        maximum_capacity
            |feedin_cap|

        Examples
        --------
        >>> from oemof.eesyplan import CarrierBus
        >>> ebus = CarrierBus(name="any_bus")
        >>> my_dso = DSO(
        ...     name="any_network",
        ...     bus=ebus,
        ...     energy_price=0.25,
        ...     feedin_tariff=0.08,
        ... )

        """
        self.name = name
        self.bus = bus
        self.maximum_capacity = maximum_capacity
        self.energy_price = energy_price
        self.feedin_tariff = feedin_tariff
        self.peak_demand_pricing = peak_demand_pricing
        self.fix_cost = basic_amount

        super().__init__(label=self.name)

        if energy_price is None and feedin_tariff is None:
            raise ValueError(
                "Either energy_price or feedin_tariff must be set"
            )

        if feedin_tariff is None:
            self.subnode(
                Sink,
                inputs={
                    self.bus: Flow(
                        variable_costs=self.feedin_tariff * -1,
                        nominal_capacity=self.maximum_capacity,
                    )
                },
                local_name="feedin_sink",
            )

        if energy_price is None:
            self.subnode(
                Source,
                outputs={
                    self.bus: Flow(
                        variable_costs=self.energy_price,
                        nominal_capacity=Investment(
                            ep_costs=self.peak_demand_pricing,
                            maximum=self.maximum_capacity,
                        ),
                    )
                },
                local_name="consumption_source",
            )
