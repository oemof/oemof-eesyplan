from numpy.typing import ArrayLike

from oemof.network import Node
from oemof.solph import Bus
from oemof.solph import Flow
from oemof.solph.components import Converter
from oemof.solph.components import Sink


class HeatingPipe(Node):
    """
    Bidirectional heating pipe.

    This component models a heating pipe that connects two heat buses. Heat
    is always transferred from bus_1_heat to bus_2_heat. If return_pipe is
    set, heat is additionally transferred back from bus_2_heat to
    bus_1_heat, so the pipe acts in both directions. Relative losses reduce
    the transferred heat in each direction. Absolute losses are drawn from
    bus_1_heat as a fixed flow.

    Args:
        name: |name|
        bus_1_heat: |bus_1_heat|
        bus_2_heat: |bus_2_heat|
        absolute_losses: (optional) -- |absolute_losses|
        relative_losses: (optional) -- |relative_losses|
        return_pipe: (optional) -- |return_pipe|

    Examples:
        >>> from oemof.eesyplan.components.buses.network import HeatingNetwork
        >>> w = HeatingNetwork(name="Heating Network West", absolute_losses=5)
        >>> e = HeatingNetwork(name="Heating Network East")
        >>> pipe1 = HeatingPipe(
        ...     name="pipe1",
        ...     bus_1_heat=w,
        ...     bus_2_heat=e,
        ...     relative_losses=0.1,
        ...     return_pipe=True,
        ...     )
        >>> pipe2 = HeatingPipe(
        ...     name="pipe2",
        ...     bus_1_heat=w,
        ...     bus_2_heat=e,
        ...     absolute_losses=1,
        ...     return_pipe=False,
        ...     )
    """

    def __init__(
        self,
        name: str,
        bus_1_heat: Bus,
        bus_2_heat: Bus,
        absolute_losses: (
            float | int | ArrayLike | None
        ) = None,  # CHECK: siehe ToDo zur Einheit
        relative_losses: float | int = 0.0,
        return_pipe: bool = True,
    ):
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
