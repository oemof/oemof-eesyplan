import numpy.typing as npt

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.eesyplan.components.providers.dso import DSO


class DsoHydrogen(DSO):
    def __init__(
        self,
        name: str,
        bus_hydrogen: CarrierBus,
        energy_price: float | int | npt.ArrayLike = 0.3,
        feedin_tariff: float | int | npt.ArrayLike = 0.1,
        peak_demand_pricing: float | int = 0,
        peak_demand_pricing_period: int = 1,
        renewable_share: float | int = 0.44,
        feedin_cap: float | int | None = None,
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
        bus_hydrogen : CarrierBus
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
            peak_demand_pricing_period=peak_demand_pricing_period,
            renewable_share=renewable_share,
            feedin_cap=feedin_cap,
        )
