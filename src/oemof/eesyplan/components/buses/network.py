from numpy import typing as npt
from oemof.solph import Flow
from oemof.solph.components import Sink
from oemof.eesyplan import CarrierBus


class HeatingNetwork(CarrierBus):
    def __init__(
        self,
        name: str,
        absolute_losses: (
            float | int | npt.ArrayLike | None
        ) = None,  # CHECK: siehe ToDo zur Einheit
    ):
        """
        Heating Network Bus

        Parameters
        ----------
        name : string
            |name|
        absolute_losses : float, optional
            |absolute_losses|

        Examples
        --------
        >>> hn = HeatingNetwork(name="Heating Network", absolute_losses=5)
        """
        self.name = name

        super().__init__(name=self.name, carrier="heat")

        if absolute_losses is not None:
            self.subnode(
                Sink,
                local_name="absolute_losses",
                inputs={self: Flow(nominal_capacity=1, fix=absolute_losses)},
            )
