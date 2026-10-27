import numpy as np
from numpy.typing import ArrayLike

from oemof.eesyplan.components.buses.carrier import Bus
from oemof.network import Node
from oemof.solph import Bus
from oemof.solph import Flow
from oemof.solph.components import Converter
from oemof.solph.components import Sink
from oemof.solph.components import Source


class DSO(Node):
    def __init__(
        self,
        name: str,
        bus: Bus,
        energy_price: float
        | int
        | ArrayLike = 0.3,  # TODO: check if default is intended here (base class)
        feedin_tariff: float
        | int
        | ArrayLike = 0.1,  # TODO: check if default is intended here (base class)
        peak_demand_pricing: float | int = 0,
        peak_demand_pricing_period: int = 1,
        renewable_share: float | int = 0.44,
        feedin_cap: float | int | None = None,
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
            bus : Carrier

        Parameters
        ----------
        name : str
            |name|
        bus : Bus
            |bus|
        energy_price : float or array-like, default=0.3
            |energy_price|
        feedin_tariff : float or array-like, default=0.1
            |feedin_tariff|
        peak_demand_pricing : float, default=0
            |peak_demand_pricing|
        peak_demand_pricing_period : int, default=1
            |peak_demand_pricing_period|
        renewable_share : float, default=0.44
            |renewable_share|
        feedin_cap : float or None, default=None
            |feedin_cap|

        Examples
        --------
        >>> from oemof.eesyplan import Bus
        >>> ebus = Bus(name="any_bus")
        >>> my_dso = DSO(
        ...     name="any_network",
        ...     bus=ebus,
        ...     energy_price=0.25,
        ...     feedin_tariff=0.08,
        ... )

        """
        self.name = name
        self.bus = bus
        if isinstance(energy_price, list):
            energy_price = np.array(energy_price)
        self.energy_price = energy_price
        if isinstance(feedin_tariff, list):
            feedin_tariff = np.array(feedin_tariff)
        self.feedin_tariff = feedin_tariff
        self.peak_demand_pricing = peak_demand_pricing
        self.peak_demand_pricing_period = peak_demand_pricing_period
        self.renewable_share = renewable_share  # Specific emission
        self.feedin_cap = feedin_cap

        super().__init__(label=self.name)

        internal_bus = self.subnode(Bus, local_name="internal_bus")

        self.subnode(
            Converter,
            inputs={self.bus: Flow(variable_costs=self.feedin_tariff * -1)},
            outputs={internal_bus: Flow()},
            local_name="feedin_converter",
        )

        self.subnode(
            Sink, inputs={internal_bus: Flow()}, local_name="feedin_sink"
        )

        self.subnode(
            Converter,
            inputs={internal_bus: Flow()},
            outputs={self.bus: Flow(variable_costs=self.energy_price)},
            local_name="consumption_converter",
        )

        self.subnode(
            Source,
            outputs={internal_bus: Flow()},
            local_name="consumption_source",
        )
