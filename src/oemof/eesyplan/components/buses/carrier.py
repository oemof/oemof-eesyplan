from oemof.solph import Bus as SolphBus
from oemof.solph import Flow
from oemof.solph.components import Sink
from oemof.solph.components import Source


class CarrierBus(SolphBus):
    """
    Bus with carrier information

    Args:
        name: |name|
        carrier: (optional) -- |carrier|
        balanced: (optional) -- |balanced|
        excess_cost: (optional) -- |excess_cost|
        shortage_cost: (optional) -- |shortage_cost|

    Examples:
        >>> electricity_bus = CarrierBus(name="grid", carrier="electricity",
        ...                      excess_cost=2)
        >>> electricity_bus.excess_cost
        2.0
        >>> heat_bus = CarrierBus(name="heating", carrier="heat")
        >>> heat_bus
        <Bus 'heating', carrier='heat', shortage: None, excess: None>
        >>> h2_bus = CarrierBus(name="h2_net", carrier="hydrogen",
        ...                     excess_cost=0, shortage_cost=99)
        >>> h2_bus
        <Bus 'h2_net', carrier='hydrogen', shortage: 99, excess: 0.0>
    """

    def __init__(
        self,
        name: str | tuple,
        carrier: str | None = None,
        balanced: bool = True,
        excess_cost: float | int | None = None,
        shortage_cost: float | int | None = None,
    ):
        super().__init__(label=name, balanced=balanced)
        self.carrier = carrier
        self.name = name
        if excess_cost is not None:
            excess_cost = float(excess_cost)
        self.excess_cost = excess_cost
        self.shortage_cost = shortage_cost

        if excess_cost is not None:
            self.subnode(
                Sink,
                local_name="excess",
                inputs={
                    self: Flow(
                        variable_costs=excess_cost,
                    )
                },
            )

        if shortage_cost is not None:
            self.subnode(
                Source,
                local_name="shortage",
                outputs={
                    self: Flow(
                        variable_costs=shortage_cost,
                    )
                },
            )

    def __repr__(self):
        return (
            f"<Bus '{self.name}', carrier='{self.carrier}', "
            f"shortage: {self.shortage_cost}, excess: {self.excess_cost}>"
        )
