from numpy.typing import ArrayLike

from oemof.eesyplan.components.demand.demand import Demand
from oemof.solph import Bus


class HeatDemand(Demand):
    """
    Heat demand/consumption component.

    This class represents a heat demand that consumes
    heat energy according to a specified time series pattern.

    Args:
        name: |name|
        bus_in_heat: |bus_in_heat|
        input_timeseries: |input_timeseries|
        carrier: (optional) -- |carrier|

    Examples:
        >>> from oemof.solph import Bus
        >>> heat_bus = Bus(label="heat_bus")
        >>> my_demand = HeatDemand(
        ...     name="office_demand",
        ...     bus_in_heat=heat_bus,
        ...     input_timeseries="heat_demand.csv",
        ... )
    """

    def __init__(
        self,
        name: str,
        bus_in_heat: Bus,
        input_timeseries: ArrayLike | str,  # CHECK: str (Dateiname) korrekt?
        carrier: str = "heat",
    ):
        super().__init__(
            name=name,
            bus_in=bus_in_heat,
            carrier=carrier,
            input_timeseries=input_timeseries,
        )
