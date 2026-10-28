from numpy.typing import ArrayLike

from oemof.eesyplan import CarrierBus
from oemof.solph import Flow
from oemof.solph.components import Sink


class HeatingNetwork(CarrierBus):
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
        """
        Heating Network Bus

        Parameters
        ----------
        name : string
            |name|
        absolute_losses : float, int or array-like, optional (default: None)
            |absolute_losses|
        excess_cost : float or int, optional (default: None)
            |excess_cost|
        shortage_cost : float or int, optional (default: None)
            |shortage_cost|

        Examples
        --------
        >>> hn = HeatingNetwork(name="Heating Network", absolute_losses=5)
        """
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
