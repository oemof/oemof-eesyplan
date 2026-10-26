import numpy.typing as npt

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.eesyplan.components.demand.demand import Demand


class ElectricityDemand(Demand):
    def __init__(
        self,
        name: str,
        bus_in_electricity: CarrierBus,
        input_timeseries: npt.ArrayLike
        | str,  # CHECK: str (Dateiname) korrekt?
        carrier: str = "electricity",
    ):
        """
        Electricity demand/consumption component.

        This class represents an electricity demand that consumes
        electrical energy according to a specified time series pattern.

        Structure
        ---------
        *input*
            1. from_bus : Electricity

        carrier : str, optional (default: "electricity")
            |carrier|

        Parameters
        ----------
        name : str
            |name|
        bus_in_electricity : oemof.eesyplan.CarrierBus
            |bus_in_electricity|
        input_timeseries : array-like
            |input_timeseries|

        Examples
        --------
        >>> from oemof.eesyplan import CarrierBus as Bus
        >>> ebus = Bus(name="electricity_bus")
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
