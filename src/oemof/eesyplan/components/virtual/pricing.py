from oemof.network import Node
from oemof.solph import Bus
from oemof.solph import Flow
from oemof.solph import Investment
from oemof.solph.components import Converter


class FlowPricing(Node):
    """
    Extra-pricing node coupling two investment capacities.

    This class models additional cost or funding.

    Variable cost can be limited to specific amount of energy.

    .. important ::
        If no ``full_load_time_limit`` the limited cost will be ignored.
        A basic amount of cost can be added to the result. This ammount is NOT
        part of the optimisation and will be ignored by the solver. Use it only
        if you know what you are doing.

    :Structure:
      *input*
        1. from_bus : ``bus_in``
      *output*
        1. to_bus : ``bus_out``

    :Optimization:
        To be written.

    Parameters
    ----------
    name : str
        Name of the component.
    bus_in : bus object
        Input bus from which the energy is drawn.
    bus_out : bus object
        Output bus into which the energy is fed.
    cost_unlimited : float or array-like, default: 0
        Variable costs fo an unlimited amount of energy.
    cost_limited : float or array-like or None, default: None
        Variable costs of a limited amount of energy. Set full load time to
        define the amount of energy. If no full load time is defined, the
        cost_limited will be ignored.
    full_load_time_limit : float or None, default: None
        Maximum full load time to define the amount of energy for the limited
        cost. If "None" the limited cost are ignored.
    maximum_capacity : float, default: float("inf")
        Maximum capacity.
    maximum_limited_path : float or array-like or None, default: None
        Time series, where the
    maximum_unlimited_path : float or array-like or None, default: None
        Time series, where the

    Examples
    --------
    >>> from oemof.eesyplan import CarrierBus
    >>> from oemof.eesyplan import FlowPricing
    >>> bus_in = CarrierBus(name="bus_in")
    >>> bus_out = CarrierBus(name="bus_out")
    >>> my_extra_pricing = FlowPricing(
    ...     name="extra_pricing_node",
    ...     bus_in=bus_in,
    ...     bus_out=bus_out,
    ...     cost_unlimited=0.1,
    ...     cost_limited=0.2,
    ...     maximum_capacity=500,
    ...     full_load_time_limit=3000,
    ... )
    >>> my_extra_pricing.full_load_time_limit
    3000
    >>> len(my_extra_pricing.subnodes)
    4

    >>> my_extra_pricing_unlimited = FlowPricing(
    ...     name="extra_pricing_unlimited",
    ...     bus_in=bus_in,
    ...     bus_out=bus_out,
    ...     cost_unlimited=0.1,
    ... )
    >>> my_extra_pricing_unlimited.full_load_time_limit is None
    True
    >>> len(my_extra_pricing_unlimited.subnodes)
    1
    """

    def __init__(
        self,
        name,
        bus_in,
        bus_out,
        maximum_capacity: float | int | None = None,
        cost_unlimited=0.0,
        cost_limited=None,
        full_load_time_limit=None,
        maximum_unlimited_path=None,
        maximum_limited_path=None,
    ):
        if full_load_time_limit is not None and maximum_capacity is None:
            raise ValueError("full_load_time_limit cannot be set to infinity")

        super().__init__(label=name)

        self.full_load_time_limit = full_load_time_limit

        if full_load_time_limit is not None:
            internal_bus = self.subnode(
                Bus, local_name="internal_bus_flow_price"
            )

            self.subnode(
                Converter,
                inputs={internal_bus: Flow(nominal_capacity=maximum_capacity)},
                outputs={bus_out: Flow()},
                local_name="flow_price_converter_limit",
            )

            self.subnode(
                Converter,
                inputs={
                    bus_in: Flow(
                        nominal_capacity=maximum_capacity,
                        variable_costs=cost_limited,
                        full_load_time_max=full_load_time_limit,
                        maximum=maximum_limited_path,
                    )
                },
                outputs={internal_bus: Flow()},
                local_name="flow_price_converter_flh",
            )
            bus_base = internal_bus

        else:
            bus_base = bus_in

        self.subnode(
            Converter,
            inputs={
                bus_in: Flow(
                    nominal_capacity=maximum_capacity,
                    variable_costs=cost_unlimited,
                    maximum=maximum_unlimited_path,
                )
            },
            outputs={bus_base: Flow()},
            local_name="flow_price_converter",
        )


class PeakPricing(Node):
    """
    Extra-pricing node coupling two investment capacities.

    This class models additional cost or funding.

    Variable cost can be limited to specific amount of energy.

    .. important ::
        If no ``full_load_time_limit`` the limited cost will be ignored.
        A basic amount of cost can be added to the result. This ammount is NOT
        part of the optimisation and will be ignored by the solver. Use it only
        if you know what you are doing.

    *Structure*
      *input*
        1. from_bus : ``bus_in``
      *output*
        1. to_bus : ``bus_out``

    Optimisation
    ++++++++++++
        To be written.

    Parameters
    ----------
    name : str
        Name of the component.
    bus_in : bus object
        Input bus from which the energy is drawn.
    bus_out : bus object
        Output bus into which the energy is fed.
    peak_price : float or None, default: None
        Peak price.
    operational_cost : float, default: 0
        Variable costs for an amount of energy.
    basic_amount : float, default: 0
        Fixed costs (basic amount) of the component. Will be added in the
        postprocessing and will be ignored in the optimisation. Only use if you
        know what you are doing.
    maximum_capacity : float, default: float("inf")
        Maximum capacity.

    Examples
    --------
    >>> from oemof.eesyplan import CarrierBus
    >>> from oemof.eesyplan import PeakPricing
    >>> bus_in = CarrierBus(name="bus_in")
    >>> bus_out = CarrierBus(name="bus_out")
    >>> my_peak_pricing = PeakPricing(
    ...     name="extra_pricing_node",
    ...     bus_in=bus_in,
    ...     bus_out=bus_out,
    ...     peak_price=500,
    ...     operational_cost=0.2,
    ...     basic_amount=100,
    ...     maximum_capacity=1000,
    ... )
    >>> my_peak_pricing.fix_cost
    100
    """

    def __init__(
        self,
        name,
        bus_in,
        bus_out,
        peak_price=None,
        operational_cost=0.0,
        basic_amount=0.0,
        maximum_capacity=float("inf"),
    ):
        super().__init__(label=name)

        self.fix_cost = basic_amount

        self.subnode(
            Converter,
            inputs={
                bus_in: Flow(
                    nominal_capacity=Investment(
                        ep_costs=peak_price, maximum=maximum_capacity
                    ),
                    variable_costs=operational_cost,
                )
            },
            outputs={bus_out: Flow()},
            local_name="peak_price_converter",
        )
