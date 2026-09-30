from oemof.eesyplan.components.providers.dso import DSO


class DsoElectricity(DSO):
    def __init__(
        self,
        name,
        bus_electricity,
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
            bus : Electricity

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
            maximum_capacity=maximum_capacity
        )
