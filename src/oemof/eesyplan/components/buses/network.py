from numpy.typing import ArrayLike

from oemof.eesyplan import CarrierBus
from oemof.solph import Flow
from oemof.solph.components import Sink


class HeatingNetwork(CarrierBus):
    """
    Heating Network Bus

    Args:
        name: |name|
        absolute_losses: (optional) -- |absolute_losses|
        excess_cost: (optional) -- |excess_cost|
        shortage_cost: (optional) -- |shortage_cost|
        investment_fix_cost: (optional) -- |investment_fix_cost|
        annual_fix_cost: (optional) -- |annual_fix_cost|

    Examples:
        >>> hn = HeatingNetwork(name="Heating Network", absolute_losses=5)
    """

    def __init__(
        self,
        name: str,
        # CHECK: see ToDo regarding the unit of absolute_losses
        absolute_losses: float | int | ArrayLike | None = None,
        excess_cost: float | int | None = None,
        shortage_cost: float | int | None = None,
        investment_fix_cost: float | int = 0,
        annual_fix_cost: float | int = 0,
    ):
        self.name = name
        self.absolute_losses = absolute_losses
        self.excess_cost = excess_cost
        self.shortage_cost = shortage_cost
        self.investment_fix_cost = investment_fix_cost
        self.annual_fix_cost = annual_fix_cost

        super().__init__(
            name=self.name,
            carrier="heat",
            excess_cost=excess_cost,
            shortage_cost=shortage_cost,
        )

        if absolute_losses is not None:
            self.subnode(
                Sink,
                local_name="absolute_losses",
                inputs={self: Flow(nominal_capacity=1, fix=absolute_losses)},
            )
