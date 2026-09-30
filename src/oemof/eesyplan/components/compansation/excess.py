from oemof.solph import Flow
from oemof.solph.components import Sink


class Excess(Sink):
    def __init__(self, name, bus_in, cost):
        """
        Short description

        Long description about the facade and how to use it.

        .. important ::
            Some important information about this facade.


        Parameters
        ----------
        name : str
            |name|
        bus_in : CarrierBus
            |bus_in|
        cost : float or array-like
            |energy_prices|

        Examples
        --------
        >>> from oemof.eesyplan import CarrierBus
        >>> el_bus = CarrierBus(name="my_electricity_bus")
        >>> ex = Excess("my_excess", el_bus, 999)
        >>> ex.label
        'my_excess'

        """
        super().__init__(
            label=name,
            inputs={
                bus_in: Flow(
                    variable_costs=cost,
                )
            },
        )
