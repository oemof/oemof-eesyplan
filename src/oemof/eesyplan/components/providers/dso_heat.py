import numpy.typing as npt

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.eesyplan.components.providers.dso import DSO


class DsoHeat(DSO):
    def __init__(
        self,
        name: str,
        bus_heat: CarrierBus,
        energy_price: float | int | npt.ArrayLike = 0.3,
        renewable_share: float | int = 0.44,
    ):
        """
        Energy provider for heat distribution.

        This class represents a distribution system operator (DSO) that
        provides heat from the utility grid with pricing and
        feedin capabilities.

        .. important ::
            The renewable share affects the overall system renewable
            factor calculation.

        Structure
        ---------
        *input* & *output*
            bus : Heat

        Parameters
        ----------
        name : str
            |name|
        bus_heat : CarrierBus
            |bus|
        energy_price : float or array-like, default=0.3
            |energy_price|
        renewable_share : float, default=0.44
            |renewable_share|

        Examples
        --------
        >>> from oemof.eesyplan import CarrierBus
        >>> hbus = CarrierBus(name="heat_bus")
        >>> my_dso = DsoHeat(
        ...     name="main_grid",
        ...     bus_heat=hbus,
        ...     energy_price=0.25,
        ... )

        """
        super().__init__(
            name=name,
            bus=bus_heat,
            energy_price=energy_price,
            renewable_share=renewable_share,
        )
