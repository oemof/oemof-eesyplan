from numpy.typing import ArrayLike

from oemof.solph import Bus
from oemof.eesyplan.components.demand.demand import Demand


class FuelDemand(Demand):
    """
    Fuel demand/consumption component.

    This class represents a fuel demand that consumes fuel
    according to a specified time series pattern.

    Args:
        name: |name|
        bus_in_fuel: |bus_in_fuel|
        input_timeseries: |input_timeseries|
        carrier: (optional) -- |carrier|

    Examples:
        >>> from oemof.solph import Bus
        >>> fuel_bus = Bus(label="fuel_bus")
        >>> my_demand = FuelDemand(
        ...     name="office_demand",
        ...     bus_in_fuel=fuel_bus,
        ...     input_timeseries="fuel_demand.csv",
        ... )
    """


    def __init__(
        self,
        name: str,
        bus_in_fuel: Bus,
        input_timeseries: (ArrayLike | str),  # CHECK: str (Dateiname) korrekt?
        carrier: str = "fuel",
    ):
        super().__init__(
            name=name,
            bus_in=bus_in_fuel,
            carrier=carrier,
            input_timeseries=input_timeseries,
        )
