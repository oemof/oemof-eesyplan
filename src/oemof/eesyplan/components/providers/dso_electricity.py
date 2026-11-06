from numpy.typing import ArrayLike

from oemof.eesyplan.components.providers.dso import DSO
from oemof.solph import Bus


class DsoElectricity(DSO):
    """
    Distribution system operator for electricity exchange.

    This component models a distribution system operator (DSO) that
    supplies electricity from the utility grid to a bus and optionally
    absorbs electricity from it. It applies the energy price to supplied
    electricity and the feedin tariff to absorbed electricity.

    .. important::
        At least one of energy_price and feedin_tariff must be set. Setting
        a maximum_feedin_capacity without a feedin_tariff raises a
        ValueError.

    Args:
        name: |name|
        bus_electricity: |bus|
        energy_price: (optional) -- |energy_price|
        feedin_tariff: (optional) -- |feedin_tariff|
        peak_demand_pricing: (optional) -- |peak_demand_pricing|
        maximum_capacity: (optional) -- |maximum_capacity|
        maximum_feedin_capacity: (optional) -- |maximum_feedin_capacity|

    Examples:
        >>> from oemof.eesyplan import CarrierBus
        >>> ebus = CarrierBus(name="electricity_bus")
        >>> my_dso = DsoElectricity(
        ...     name="main_grid",
        ...     bus_electricity=ebus,
        ...     energy_price=0.25,
        ...     feedin_tariff=0.08,
        ...     )
        >>> my_dso.name
        'main_grid'
    """

    def __init__(
        self,
        name: str,
        bus_electricity: Bus,
        energy_price: float | int | ArrayLike | None = None,
        feedin_tariff: float | int | ArrayLike | None = None,
        peak_demand_pricing: float | int = 0,
        maximum_capacity: float | int | None = None,
        maximum_feedin_capacity: float | int | None = None,
    ):
        super().__init__(
            name=name,
            bus=bus_electricity,
            energy_price=energy_price,
            feedin_tariff=feedin_tariff,
            peak_demand_pricing=peak_demand_pricing,
            maximum_capacity=maximum_capacity,
            maximum_feedin_capacity=maximum_feedin_capacity,
        )
