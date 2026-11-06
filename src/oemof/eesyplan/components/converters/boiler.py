from numpy.typing import ArrayLike

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.eesyplan.project import Project
from oemof.solph import Flow
from oemof.solph.components import Converter


class Boiler(Converter):
    """
    Boiler for heat generation.

    This class represents a boiler that burns fuel into
    thermal energy for heating applications.

    .. important::
        The efficiency parameter determines the conversion rate
        from fuel to thermal output.

    Optimisation:
        The characteristic quantity of the optimisation is the *maximum
        power-output* of the Boiler given in kW

    Args:
        name: |name|
        bus_in: |bus_in|
        bus_out_heat: |bus_out_heat|
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
        >>> heat_bus = CarrierBus(name="heat_bus")
        >>> my_fuel_boiler = Boiler(
        ...     name="central_fuel_boiler",
        ...     bus_in=fuel_bus,
        ...     bus_out_heat=heat_bus,
        ...     age_installed=0,
        ...     capex_spec=1000,
        ...     opex_spec=1000,
        ...     lifetime=20,
        ...     maximum_capacity=1000,
        ...     efficiency=0.8,
        ...     variable_costs=0,
        ...     project_data=Project(
        ...         name="Project_X", economic_period=20, tax=0,
        ...         discount_factor=0.01),
        ...     )

    """

    def __init__(
        self,
        name: str,
        bus_in: CarrierBus,
        bus_out_heat: CarrierBus,
        project_data: Project,
        efficiency: float | int | ArrayLike = 0.8,  # CHECK
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

        inputs = {bus_in: Flow()}

        outputs = {
            bus_out_heat: Flow(
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
            conversion_factors={bus_out_heat: efficiency},
        )
