from numpy.typing import ArrayLike

from oemof.eesyplan import Bus
from oemof.network import Node
from oemof.solph import Flow
from oemof.solph.components import Converter
from oemof.solph.components import Sink


class HeatingPipe(Node):
    def __init__(
        self,
        name: str,
        bus_1_heat: Bus,
        bus_2_heat: Bus,
        absolute_losses: float
        | int
        | ArrayLike
        | None = None,  # CHECK: siehe ToDo zur Einheit
        relative_losses: float | int = 0.0,
        return_pipe: bool = True,
    ):
        """
        Bidirectional Heating Pipe.

        Parameters
        ----------
        name : string
            |name|
        bus_1_heat : Node object
            |bus_1_heat|
        bus_2_heat : Node object
            |bus_2_heat|
        absolute_losses : float, optional (default: None)
            |absolute_losses|
        relative_losses : float, optional (default: 0.0)
            |relative_losses|
        return_pipe : bool, optional (default: True)
            |return_pipe|

        Examples
        --------
        >>> from oemof.eesyplan.components.buses.network import HeatingNetwork
        >>> w = HeatingNetwork(name="Heating Network West", absolute_losses=5)
        >>> e = HeatingNetwork(name="Heating Network East")
        >>> pipe1 =HeatingPipe(name="pipe1", bus_1_heat=w, bus_2_heat=e,
        ...                    relative_losses=0.1, return_pipe=True)
        >>> pipe2 =HeatingPipe(name="pipe1", bus_1_heat=w, bus_2_heat=e,
        ...                    absolute_losses=1, return_pipe=False)

        """
        self.name = name

        super().__init__(label=self.name)

        self.subnode(
            Converter,
            inputs={bus_1_heat: Flow()},
            outputs={bus_2_heat: Flow()},
            local_name="heat_pipeline_1_2",
            conversion_factors={bus_2_heat: (1 - relative_losses)},
        )
        if return_pipe:
            self.subnode(
                Converter,
                inputs={bus_2_heat: Flow()},
                outputs={bus_1_heat: Flow()},
                local_name="heat_pipeline_2_1",
                conversion_factors={bus_1_heat: (1 - relative_losses)},
            )
        if absolute_losses is not None:
            self.subnode(
                Sink,
                local_name="absolute_losses",
                inputs={
                    bus_1_heat: Flow(nominal_capacity=1, fix=absolute_losses)
                },
            )
