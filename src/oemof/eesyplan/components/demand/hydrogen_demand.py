from numpy.typing import ArrayLike

from oemof.eesyplan.components.demand.demand import Demand
from oemof.solph import Bus


class H2Demand(Demand):
    """
    Hydrogen demand/consumption component.

    This class represents a hydrogen demand that consumes hydrogen
    according to a specified time series pattern.

    Args:
        name: |name|
        bus_in_hydrogen: |bus_in_hydrogen|
        input_timeseries: |input_timeseries|
        carrier: (optional) -- |carrier|

    Examples:
        >>> from oemof.solph import Bus
        >>> h2_bus = Bus(label="hydrogen_bus")
        >>> my_h2_demand = H2Demand(
        ...     name="fuel_cell_demand",
        ...     bus_in_hydrogen=h2_bus,
        ...     input_timeseries="hydrogen_demand.csv",
        ... )
    """

    def __init__(
        self,
        name: str,
        bus_in_hydrogen: Bus,
        input_timeseries: ArrayLike | str,  # CHECK: str (Dateiname) korrekt?
        carrier: str = "hydrogen",
    ):
        super().__init__(
            name=name,
            bus_in=bus_in_hydrogen,
            carrier=carrier,
            input_timeseries=input_timeseries,
        )
