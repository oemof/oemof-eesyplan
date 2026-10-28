from numpy.typing import ArrayLike

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.eesyplan.components.providers.dso import DSO


class DsoHydrogen(DSO):
    def __init__(
        self,
        name: str,
        bus_hydrogen: CarrierBus,
        energy_price: float | int | ArrayLike | None = None,
        feedin_tariff: float | int | ArrayLike | None = None,
        peak_demand_pricing: float | int = 0,
        maximum_capacity: float | int = float("inf"),
    ):
        """
        Energy provider for hydrogen distribution.

        This class represents a distribution system operator (DSO) that
        provides hydrogen from the utility grid with pricing and
        feedin capabilities.

        .. important ::
            The renewable share affects the overall system renewable
            factor calculation.

        Structure
        ---------
        *input* & *output*
            bus : Hydrogen

        Parameters
        ----------
        name : str
            |name|
        bus_hydrogen
            |bus|
        maximum_capacity
            |maximum_capacity|
        energy_price
            |energy_prices|
        feedin_tariff
            |feedin_tariff|
        peak_demand_pricing
            |peak_demand_pricing|

        Examples
        --------
        >>> from oemof.eesyplan import CarrierBus
        >>> h2bus = CarrierBus(name="h2_bus")
        >>> my_dso = DsoHydrogen(
        ...     name="main_grid",
        ...     bus_hydrogen=h2bus,
        ...     energy_price=0.25,
        ...     feedin_tariff=0.08,
        ... )

        """
        super().__init__(
            name=name,
            bus=bus_hydrogen,
            energy_price=energy_price,
            feedin_tariff=feedin_tariff,
            peak_demand_pricing=peak_demand_pricing,
            maximum_capacity=maximum_capacity,
        )
