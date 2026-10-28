from numpy.typing import ArrayLike

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.solph.components import Source
from oemof.solph.flows import Flow


class Shortage(Source):
    """
    Source for energy shortage.

    This class represents a flexible source that supplies missing
    energy into a bus at a given cost. It is typically used to
    avoid an infeasible optimisation problem when demand exceeds
    the available supply in the system, by allowing the model to
    cover the deficit at a cost.

    .. important ::
        The cost parameter should usually be set high enough to
        discourage the optimisation from relying on this source,
        so that it only supplies energy when strictly necessary.

    Args:
        name: |name|
        bus_out: |bus_out|
        cost: (optional) -- |shortage_cost|

    Examples:
        >>> from oemof.eesyplan import CarrierBus
        >>> el_bus = CarrierBus(name="my_electricity_bus")
        >>> ex = Shortage("my_shortage", el_bus, 999)
        >>> ex.label
        'my_shortage'
    """

    def __init__(
        self,
        name: str,
        bus_out: CarrierBus,
        cost: float | int | ArrayLike = 0,
    ):
        super().__init__(
            label=name,
            outputs={
                bus_out: Flow(
                    variable_costs=cost,
                )
            },
        )
