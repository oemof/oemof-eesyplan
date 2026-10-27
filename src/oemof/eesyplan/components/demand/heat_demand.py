import numpy.typing as npt

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.eesyplan.components.demand.demand import Demand


class HeatDemand(Demand):
    def __init__(
        self,
        name: str,
        bus_in_heat: CarrierBus,
        input_timeseries: npt.ArrayLike
        | str,  # CHECK: str (Dateiname) korrekt?
        carrier: str = "heat",
    ):
        """
        Heat demand/consumption component.

        This class represents a heat demand that consumes
        heat energy according to a specified time series pattern.

        Structure
        ---------
        *input*
            1. from_bus : Heat
        carrier : str, optional (default: "heat")
            |carrier|

        Parameters
        ----------
        name : str
            |name|
        bus_in_heat : oemof.eesyplan.CarrierBus
            |bus_in_heat|
        input_timeseries : array-like
            |input_timeseries|

        Examples
        --------
        >>> from oemof.eesyplan import CarrierBus as Bus
        >>> heat_bus = Bus(name="heat_bus")
        >>> my_demand = HeatDemand(
        ...     name="office_demand",
        ...     bus_in_heat=heat_bus,
        ...     input_timeseries="heat_demand.csv",
        ... )

        """

        super().__init__(
            name=name,
            bus_in=bus_in_heat,
            carrier=carrier,
            input_timeseries=input_timeseries,
        )
