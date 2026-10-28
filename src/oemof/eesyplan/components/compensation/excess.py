from numpy.typing import ArrayLike

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.solph import Flow
from oemof.solph.components import Sink


class Excess(Sink):
    """
    Sink for excess energy.

    This class represents a flexible sink that absorbs surplus
    energy from a bus at a given cost. It is typically used to
    avoid an infeasible optimisation problem when more energy is
    available in the system than can be consumed or stored, by
    allowing the model to dispose of excess energy at a cost.

    .. important ::
        The cost parameter should usually be set high enough to
        discourage the optimisation from relying on this sink,
        unless it is deliberately used to represent a cost-free
        energy outlet (e.g. curtailment).

    Args:
        name: |name|
        bus_in: |bus_in|
        cost: (optional) -- |excess_cost|

    Examples:
        >>> from oemof.eesyplan import CarrierBus
        >>> el_bus = CarrierBus(name="my_electricity_bus")
        >>> ex = Excess("my_excess", el_bus, 999)
        >>> ex.label
        'my_excess'
    """

    def __init__(
        self,
        name: str,
        bus_in: CarrierBus,
        cost: float | int | ArrayLike = 0,
    ):
        super().__init__(
            label=name,
            inputs={
                bus_in: Flow(
                    variable_costs=cost,
                )
            },
        )
