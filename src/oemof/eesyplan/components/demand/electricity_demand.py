from numpy.typing import ArrayLike

from oemof.solph import Bus
from oemof.eesyplan.components.demand.demand import Demand


class ElectricityDemand(Demand):
    def __init__(
        self,
        name: str,
        bus_in_electricity: Bus,
        input_timeseries: ArrayLike | str,  # CHECK: str (Dateiname) korrekt?
        carrier: str = "electricity",
    ):
        """
        Electricity demand/consumption component.

        This class represents an electricity demand that consumes
        electrical energy according to a specified time series pattern.

        Args:
            name: |name|
            bus_in_electricity: |bus_in_electricity|
            input_timeseries: |input_timeseries|
            carrier: (optional) -- |carrier|

        Examples:
            >>> from oemof.eesyplan import CarrierBus
            >>> ebus = CarrierBus(name="electricity_bus")
            >>> my_demand = ElectricityDemand(
            ...     name="office_demand",
            ...     bus_in_electricity=ebus,
            ...     input_timeseries="electricity_demand.csv",
            ... )
        """

        super().__init__(
            name=name,
            bus_in=bus_in_electricity,
            carrier=carrier,
            input_timeseries=input_timeseries,
        )
