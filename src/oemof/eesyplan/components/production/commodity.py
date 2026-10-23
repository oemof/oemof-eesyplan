import numpy.typing as npt

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.solph import Flow
from oemof.solph.components import Source


class Commodity(Source):
    def __init__(
        self,
        name: str,
        bus_out: CarrierBus,
        commodity: str | None = None,
        capacity: float | int | None = None,
        full_load_time_max: float | int | None = None,
        variable_costs: float | int | npt.ArrayLike = 0,
    ):
        """
        General Commodity.

        Parameters
        ----------
        name : string
            |name|
        bus_out : Node object
            |bus_out|
        commodity : string
            |commodity|
        capacity : float
            |capacity|
        full_load_time_max : float, optional
            |full_load_time_max|
        variable_costs : float, optional
            |variable_costs|

        Examples
        --------
        >>> # Limited by the capacity in yearly system with houry time steps.
        >>> # In every time step the output will be between 0 and 10
                >>> from oemof.eesyplan import CarrierBus
        >>> gas_bus = CarrierBus(name="natural_gas_bus")
        >>> wood = Commodity(
        ...     name="Commodity",
        ...     bus_out=gas_bus,
        ...     commodity="natural_gas",
        ...     capacity=10,
        ...     full_load_time_max=8760
        ... )
        >>> # Limited by the amount of energy. The total energy can be used in
        >>> # one timestep or can be used in 10 units in every time step. And
        >>> # everything between. Typically, a following boiler will restrict
        >>> # the capacity.
        >>> from oemof.eesyplan import CarrierBus
        >>> wood_bus = CarrierBus(name="wood_bus")
        >>> wood = Commodity(
        ...     name="Commodity",
        ...     bus_out=wood_bus,
        ...     commodity="wood",
        ...     capacity=87600,
        ...     full_load_time_max=1
        ... )
        """
        self.name = name
        self.bus_out = bus_out
        self.commodity = commodity
        self.capacity = capacity
        self.full_load_time_max = full_load_time_max
        self.variable_costs = variable_costs

        super().__init__(
            label=name,
            outputs={
                bus_out: Flow(
                    nominal_capacity=capacity,
                    full_load_time_max=full_load_time_max,
                    variable_costs=variable_costs,
                )
            },
        )
