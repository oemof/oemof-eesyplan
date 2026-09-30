from oemof.eesyplan.components.providers.dso import DSO


class DsoFuel(DSO):
    def __init__(
        self,
        name,
        bus_fuel,
        energy_price=0.3,
        feedin_tariff=0.1,
        peak_demand_pricing=0,
        maximum_capacity=None,
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
            bus : Fuel

        Parameters
        ----------
        name : str
            |name|
        maximum_capacity : float or None, default: None
            |maximum_capacity|
        energy_price : float or None, default=0.3
            |energy_prices|
        feedin_tariff : float or None, default=0.1
            |feedin_tariff|
        peak_demand_pricing : float, default=0
            |peak_demand_pricing|

        Examples
        --------
        >>> from oemof.eesyplan import CarrierBus
        >>> gbus = CarrierBus(name="gas_bus")
        >>> my_dso = DsoFuel(
        ...     name="main_grid",
        ...     bus_fuel=gbus,
        ...     energy_price=0.25,
        ...     feedin_tariff=0.08,
        ... )

        """
        super().__init__(
            name=name,
            bus=bus_fuel,
            energy_price=energy_price,
            feedin_tariff=feedin_tariff,
            peak_demand_pricing=peak_demand_pricing,
            maximum_capacity=maximum_capacity
        )
