from numpy.typing import ArrayLike

from oemof.eesyplan.components.providers.dso import DSO
from oemof.solph import Bus


class DsoFuel(DSO):
    """
    Distribution system operator for fuel exchange.

    This component models a distribution system operator (DSO) that
    supplies fuel to a bus and optionally absorbs fuel from it. It applies
    the energy price to supplied fuel and the feedin tariff to absorbed
    fuel.

    .. important::
        At least one of energy_price and feedin_tariff must be set.

    Args:
        name: |name|
        bus_fuel: |bus|
        energy_price: (optional) -- |energy_price|
        feedin_tariff: (optional) -- |feedin_tariff|
        peak_demand_pricing: (optional) -- |peak_demand_pricing|
        maximum_capacity: (optional) -- |maximum_capacity|

    Examples:
        >>> from oemof.eesyplan import CarrierBus
        >>> fbus = CarrierBus(name="fuel_bus")
        >>> my_dso = DsoFuel(
        ...     name="main_grid",
        ...     bus_fuel=fbus,
        ...     energy_price=0.25,
        ...     feedin_tariff=0.08,
        ...     )
    """

    def __init__(
        self,
        name: str,
        bus_fuel: Bus,
        energy_price: float | int | ArrayLike | None = None,
        feedin_tariff: float | int | ArrayLike | None = None,
        peak_demand_pricing: float | int = 0,
        maximum_capacity: float | int | None = None,
    ):
        super().__init__(
            name=name,
            bus=bus_fuel,
            energy_price=energy_price,
            feedin_tariff=feedin_tariff,
            peak_demand_pricing=peak_demand_pricing,
            maximum_capacity=maximum_capacity,
        )
