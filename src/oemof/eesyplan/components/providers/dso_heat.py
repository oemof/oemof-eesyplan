from numpy.typing import ArrayLike

from oemof.eesyplan.components.providers.dso import DSO
from oemof.solph import Bus


class DsoHeat(DSO):
    """
    Distribution system operator for heat exchange.

    This component models a distribution system operator (DSO) that
    supplies heat to a bus and optionally absorbs heat from it. It applies
    the energy price to supplied heat and the feedin tariff to absorbed
    heat.

    .. important::
        At least one of energy_price and feedin_tariff must be set.

    Args:
        name: |name|
        bus_heat: |bus|
        energy_price: (optional) -- |energy_price|
        feedin_tariff: (optional) -- |feedin_tariff|
        peak_demand_pricing: (optional) -- |peak_demand_pricing|
        maximum_capacity: (optional) -- |maximum_capacity|

    Examples:
        >>> from oemof.eesyplan import CarrierBus
        >>> hbus = CarrierBus(name="heat_bus")
        >>> my_dso = DsoHeat(
        ...     name="main_grid",
        ...     bus_heat=hbus,
        ...     energy_price=0.25,
        ...     feedin_tariff=0.08,
        ...     )
    """

    def __init__(
        self,
        name: str,
        bus_heat: Bus,
        energy_price: float | int | ArrayLike | None = None,
        feedin_tariff: float | int | ArrayLike | None = None,
        peak_demand_pricing: float | int = 0,
        maximum_capacity: float | int | None = None,
    ):
        super().__init__(
            name=name,
            bus=bus_heat,
            energy_price=energy_price,
            feedin_tariff=feedin_tariff,
            peak_demand_pricing=peak_demand_pricing,
            maximum_capacity=maximum_capacity,
        )
