from numpy.typing import ArrayLike

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.eesyplan.components.demand.demand import Demand


class FuelDemand(Demand):
    def __init__(
        self,
        name: str,
        bus_in_fuel: CarrierBus,
        input_timeseries: (ArrayLike | str),  # CHECK: str (Dateiname) korrekt?
        carrier: str = "fuel",
    ):
        """
        Fuel demand/consumption component.

        This class represents a fuel demand that consumes fuel
        according to a specified time series pattern.

        Structure
        ---------
            *input*
                1. from_bus : Fuel

        Parameters
        ----------
        name : str
            |name|
        bus_in_fuel : oemof.eesyplan.CarrierBus
            |bus_in_fuel|
        input_timeseries : array-like
            |input_timeseries|
        carrier : str, optional (default: "fuel")
            |carrier|

        Examples
        --------
        >>> from oemof.eesyplan import CarrierBus as Bus
        >>> fuel_bus = CarrierBus(name="fuel_bus")
        >>> my_demand = FuelDemand(
        ...     name="office_demand",
        ...     bus_in_fuel=fuel_bus,
        ...     input_timeseries="fuel_demand.csv",
        ... )

        """

        super().__init__(
            name=name,
            bus_in=bus_in_fuel,
            carrier=carrier,
            input_timeseries=input_timeseries,
        )
