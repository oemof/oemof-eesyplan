from numpy.typing import ArrayLike

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.eesyplan.project import Project
from oemof.solph import Flow
from oemof.solph.components import Converter


class FuelGenerator(Converter):
    """
    Fuel generator for electricity generation e.g. diesel generator.

    This class represents a fuel generator that converts fuel
    into electrical energy for backup or primary power generation.

    .. important ::
        The efficiency parameter determines the conversion rate
        from fuel to electrical power.

    Optimisation:
        The characteristic quantity of the optimization is the *maximum
        power-output* of the Generator given in kW

    Args:
        name: |name|
        bus_in_fuel: |bus_in_fuel|
        bus_out_electricity: |bus_out_electricity|
        project_data: |project_data|
        efficiency: (optional) -- |efficiency|
        age_installed: (optional) -- |age_installed|
        installed_capacity: (optional) -- |installed_capacity|
        maximum_capacity: (optional) -- |maximum_capacity|
        capex_spec: (optional) -- |capex_spec|
        opex_spec: (optional) -- |opex_spec|
        variable_costs: (optional) -- |variable_costs|
        lifetime: (optional) -- |lifetime|

    Examples:
        >>> from oemof.eesyplan import Project
        >>> from oemof.eesyplan import CarrierBus
        >>> fuel_bus = CarrierBus(name="fuel_bus")
        >>> el_bus = CarrierBus(name="el_bus")
        >>> my_diesel_generator = FuelGenerator(
        ...     name="DieselGenerator",
        ...     bus_in_fuel=fuel_bus,
        ...     bus_out_electricity=el_bus,
        ...     age_installed=0,
        ...     maximum_capacity=1000,
        ...     capex_spec=1000,
        ...     opex_spec=1000,
        ...     lifetime=20,
        ...     efficiency=0.3,
        ...     variable_costs=0,
        ...     project_data=Project(
        ...         name="Project_X", economic_period=20, tax=0,
        ...         discount_factor=0.01),
        ...     )
    """

    def __init__(
        self,
        name: str,
        bus_in_fuel: CarrierBus,
        bus_out_electricity: CarrierBus,
        project_data: Project,
        efficiency: float | int | ArrayLike = 0.3,  # CHECK
        age_installed: float | int = 0,
        installed_capacity: float | int | None = None,
        maximum_capacity: float | int | None = None,
        capex_spec: float | int = 1000,
        opex_spec: float | int | ArrayLike = 10,  # CHECK
        variable_costs: float | int | ArrayLike = 0,
        lifetime: float | int = 20,
    ):
        nv = project_data.create_invest_if_wanted(
            capex_spec=capex_spec,
            opex_spec=opex_spec,
            lifetime=lifetime,
            installed_capacity=installed_capacity,
            maximum_capacity=maximum_capacity,
        )

        inputs = {bus_in_fuel: Flow()}

        outputs = {
            bus_out_electricity: Flow(
                nominal_capacity=nv,
                variable_costs=variable_costs,
            )
        }

        self.name = name
        self.age_installed = age_installed
        self.installed_capacity = installed_capacity

        self.capex_spec = capex_spec
        self.opex_spec = opex_spec
        self.variable_costs = variable_costs
        self.lifetime = lifetime
        self.maximum_capacity = maximum_capacity
        self.efficiency = efficiency
        super().__init__(
            label=name,
            outputs=outputs,
            inputs=inputs,
            conversion_factors={bus_out_electricity: efficiency},
        )
