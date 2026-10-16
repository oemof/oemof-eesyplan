import numpy.typing as npt

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.eesyplan.components.providers.dso import DSO


class DsoHydrogen(DSO):
    def __init__(
        self,
        name: str,
        bus_hydrogen: CarrierBus,
        energy_price: float | int | npt.ArrayLike = 0.3,
        renewable_share: float | int = 0.44,
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
        renewable_share : float, default=0.44
            |renewable_share|

        Examples
        --------
        >>> from oemof.eesyplan import CarrierBus
        >>> h2bus = CarrierBus(name="h2_bus")
        >>> my_dso = DsoHydrogen(
        ...     name="main_grid",
        ...     bus_hydrogen=h2bus,
        ...     energy_price=0.25,
        ... )

        """
        super().__init__(
            name=name,
            bus=bus_hydrogen,
            energy_price=energy_price,
            renewable_share=renewable_share,
        )
