from numpy.typing import ArrayLike

from oemof.eesyplan.components.providers.dso import DSO
from oemof.solph import Bus


class DsoElectricity(DSO):
    def __init__(
        self,
        name: str,
        bus_electricity: Bus,
        energy_price: float | int | ArrayLike | None = None,
        feedin_tariff: float | int | ArrayLike | None = None,
        peak_demand_pricing: float | int = 0,
        maximum_capacity: float | int = float("inf"),
    ):
        """
        Energy provider for electricity distribution.

        This class represents a distribution system operator (DSO) that
        provides electricity from the utility grid with pricing and
        feedin capabilities.

        .. important ::
            The renewable share affects the overall system renewable
            factor calculation.

        Structure
        ---------
        *input* & *output*
            bus : Electricity

        Parameters
        ----------
        name
            |name|
        bus_electricity
            |bus|
        maximum_capacity
            |maximum_capacity|
        energy_price
            |energy_price|
        feedin_tariff
            |feedin_tariff|
        peak_demand_pricing
            |peak_demand_pricing|

        Examples
        --------
        >>> from oemof.eesyplan import CarrierBus
        >>> ebus = CarrierBus(name="electricity_bus")
        >>> my_dso = DsoElectricity(
        ...     name="main_grid",
        ...     bus_electricity=ebus,
        ...     energy_price=0.25,
        ...     feedin_tariff=0.08,
        ... )
        >>> my_dso.name
        'main_grid'

        """
        super().__init__(
            name=name,
            bus=bus_electricity,
            energy_price=energy_price,
            feedin_tariff=feedin_tariff,
            peak_demand_pricing=peak_demand_pricing,
            maximum_capacity=maximum_capacity,
        )
