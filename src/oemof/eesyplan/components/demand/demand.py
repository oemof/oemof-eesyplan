from numpy.typing import ArrayLike

from oemof.solph import Bus
from oemof.solph import Flow
from oemof.solph.components import Sink


class Demand(Sink):
    """
    Demand/consumption component.

    This class represents a demand that consumes energy according to a
    specified time series pattern.

    Args:
        name: |name|
        bus_in: |bus_in|
        input_timeseries: |input_timeseries|
        carrier: (optional) -- |carrier|

    Examples:
        >>> from oemof.solph import Bus
        >>> ebus = Bus(label="electricity_bus")
        >>> my_demand = Demand(
        ...     name="office_demand",
        ...     carrier="electricity",
        ...     bus_in=ebus,
        ...     input_timeseries="electricity_demand.csv",
        ... )
    """

    def __init__(
        self,
        name: str,
        bus_in: Bus,
        input_timeseries: ArrayLike
        | str,  # CHECK: str (Dateiname) korrekt - TODO Docstring anpassen?
        carrier: str | None = None,
    ):
        self.profile = input_timeseries
        self.name = name
        self.carrier = carrier

        super().__init__(
            label=name,
            inputs={
                bus_in: Flow(
                    fix=input_timeseries,
                    nominal_capacity=1,
                )
            },
        )
