from oemof.eesyplan.components.providers.dso import DSO


class DsoFuel(DSO):
    def __init__(
        self,
        name,
        bus_fuel,
        energy_price=0.3,
        renewable_share=0.44,
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
        energy_price : float or array-like, default=0.3
            |energy_prices|
        renewable_share : float, default=0.44
            |renewable_share|

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
            renewable_share=renewable_share,
        )
