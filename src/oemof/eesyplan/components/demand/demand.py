from numpy.typing import ArrayLike

from oemof.eesyplan.components.buses.carrier import Bus
from oemof.solph import Flow
from oemof.solph.components import Sink


class Demand(Sink):
    def __init__(
        self,
        name: str,
        bus_in: Bus,
        input_timeseries: ArrayLike
        | str,  # CHECK: str (Dateiname) korrekt - TODO Docstring anpassen?
        carrier: str | None = None,
    ):
        """
        Demand/consumption component.

        This class represents a demand that consumes energy according to a
        specified time series pattern.

        Structure
        ---------
        *input*
            1. from_bus : Carrier

        Parameters
        ----------
        name : str
            |name|
        bus_in : oemof.eesyplan.Bus
            |bus_in|
        input_timeseries : array-like
            |input_timeseries|
        carrier : str
            |carrier|

        Examples
        --------
        >>> from oemof.eesyplan import Bus as Bus
        >>> ebus = Bus(name="electricity_bus")
        >>> my_demand = Demand(
        ...     name="office_demand",
        ...     carrier="electricity",
        ...     bus_in=ebus,
        ...     input_timeseries="electricity_demand.csv",
        ... )

        """

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
