import numpy as np
from numpy.typing import ArrayLike

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.eesyplan.project import Project
from oemof.eesyplan.type_checks import to_array_or_number
from oemof.solph import Flow
from oemof.solph.components import VariableSplitConverter


class ChpVariableRatio(VariableSplitConverter):
    """
    Combined Heat and Power (CHP) plant.

    This class represents a combined heat and power plant that
    simultaneously generates electricity and useful heat from a
    single fuel source.

    .. important ::
        CHP systems achieve higher overall efficiency by utilising
        waste heat for useful purposes.

    Optimisation:
        The characteristic quantity of the optimisation is the
        *maximum electricity power-output (active power)* of the CHP given
        in kW.

    Args:
        name: |name|
        bus_in_fuel: |bus_in_fuel|
        bus_out_electricity: |bus_out_electricity|
        bus_out_heat: |bus_out_heat|
        efficiency_electricity_state_a: |efficiency_electricity_state_a|
        efficiency_electricity_state_b: |efficiency_electricity_state_b|
        efficiency_heat_state_a: |efficiency_heat_state_a|
        efficiency_heat_state_b: |efficiency_heat_state_b|
        project_data: |project_data|
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
        >>> el_bus = CarrierBus(name="electricity_bus")
        >>> my_chp_fixed = ChpVariableRatio(
        ...     name="variable_ratio_chp",
        ...     bus_in_fuel=fuel_bus,
        ...     bus_out_heat=heat_bus,
        ...     bus_out_electricity=el_bus,
        ...     maximum_capacity=1000,
        ...     efficiency_electricity_state_a=0.5,
        ...     efficiency_heat_state_a = 0,
        ...     efficiency_electricity_state_b=0.3,
        ...     efficiency_heat_state_b=0.5,
        ...     capex_spec=1500,
        ...     opex_spec=15,
        ...     lifetime=20,
        ...     project_data=Project(
        ...         name="Project_X", economic_period=20, tax=0,
        ...         discount_factor=0.01,
        ...     )
        ... )
    """

    def __init__(
        self,
        name: str,
        bus_in_fuel: CarrierBus,
        bus_out_electricity: CarrierBus,
        bus_out_heat: CarrierBus,
        efficiency_electricity_state_a: float | int | ArrayLike,
        efficiency_electricity_state_b: float | int | ArrayLike,
        efficiency_heat_state_a: float | int | ArrayLike,
        efficiency_heat_state_b: float | int | ArrayLike,
        project_data: Project,
        age_installed: float | int = 0,
        installed_capacity: float | int | None = None,
        maximum_capacity: float | int | None = None,
        capex_spec: float | int = 1000,
        opex_spec: float | int | ArrayLike = 10,  # CHECK
        variable_costs: float | int | ArrayLike = 0,
        lifetime: float | int = 20,
    ):
        self.efficiency_electricity_state_a = to_array_or_number(
            efficiency_electricity_state_a
        )
        self.efficiency_heat_state_a = to_array_or_number(
            efficiency_heat_state_a
        )
        self.efficiency_electricity_state_b = to_array_or_number(
            efficiency_electricity_state_b
        )
        self.efficiency_heat_state_b = to_array_or_number(
            efficiency_heat_state_b
        )
        if (
            np.asarray(self.efficiency_electricity_state_a)
            + np.asarray(self.efficiency_heat_state_a)
            > 1.0
        ).any():
            raise ValueError(
                "Total efficiency at state a is above 100% in at least one "
                "time step."
            )
        if np.asarray(
            self.efficiency_electricity_state_b + self.efficiency_heat_state_b
            > 1.0
        ).any():
            raise ValueError(
                "Total efficiency at state b is above 100% in at least one "
                "time step."
            )

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
            ),
            bus_out_heat: Flow(),
        }

        self.age_installed = age_installed
        self.installed_capacity = installed_capacity
        self.capex_spec = capex_spec
        self.opex_spec = opex_spec
        self.variable_costs = variable_costs
        self.lifetime = lifetime

        self.maximum_capacity = maximum_capacity
        self.efficiency_electricity_state_a = efficiency_electricity_state_a
        self.efficiency_heat_state_a = efficiency_heat_state_a
        self.efficiency_electricity_state_b = efficiency_electricity_state_b
        self.efficiency_heat_state_b = efficiency_heat_state_b

        super().__init__(
            label=name,
            outputs=outputs,
            inputs=inputs,
            conversion_factors={
                bus_out_electricity: efficiency_electricity_state_a,
                bus_out_heat: efficiency_heat_state_a,
            },
            conversion_factors_secondary_state={
                bus_out_electricity: efficiency_electricity_state_b,
                bus_out_heat: efficiency_heat_state_b,
            },
        )
