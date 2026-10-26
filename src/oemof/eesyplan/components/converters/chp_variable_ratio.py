import numpy.typing as npt

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.eesyplan.project import Project
from oemof.solph import Flow
from oemof.solph.components import VariableSplitConverter


class ChpVariableRatio(VariableSplitConverter):
    def __init__(
        self,
        name: str,
        bus_in_fuel: CarrierBus,
        bus_out_electricity: CarrierBus,
        bus_out_heat: CarrierBus,
        efficiency_electricity_state_a: float | int | npt.ArrayLike,
        efficiency_electricity_state_b: float | int | npt.ArrayLike,
        efficiency_heat_state_a: float | int | npt.ArrayLike,
        efficiency_heat_state_b: float | int | npt.ArrayLike,
        project_data: Project,
        age_installed: float | int = 0,
        installed_capacity: float | int | None = None,
        maximum_capacity: float | int | None = None,
        capex_spec: float | int = 1000,
        opex_spec: float | int | npt.ArrayLike = 10,  # CHECK
        variable_costs: float | int | npt.ArrayLike = 0,
        lifetime: float | int = 20,
    ):
        """
        Combined Heat and Power (CHP) plant.

        This class represents a combined heat and power plant that
        simultaneously generates electricity and useful heat from a
        single fuel source.

        .. important ::
            CHP systems achieve higher overall efficiency by utilising
            waste heat for useful purposes.

        Structure
        ---------
          *input*
            1. bus_in_fuel : Fuel
          *output*
            1. bus_out_heat : Heat
            2. bus_out_electricity : Electricity

        Optimisation
        ------------
          The characteristic quantity of the optimisation is the
          *maximum electricity
          power-output (active power)* of the CHP given in kW

        Parameters
        ----------
        name : str
            |name|
        bus_in_fuel : CarrierBus
            |bus_in_fuel|
        bus_out_electricity : CarrierBus
            |bus_out_electricity|
        bus_out_heat : CarrierBus
            |bus_out_heat|
        efficiency_electricity_state_a : float
            |efficiency_electricity_state_a|
        efficiency_electricity_state_b : float
            |efficiency_electricity_state_b|
        efficiency_heat_state_a : float
            |efficiency_heat_state_a|
        efficiency_heat_state_b : float
            |efficiency_heat_state_b|
        project_data : Project object
            |project_data|
        age_installed : int, default=0
            |age_installed|
        installed_capacity : float or None (default: None)
            |installed_capacity|
        maximum_capacity : float or None (default: None)
            |maximum_capacity|
        capex_spec : float, default=1000
            |capex_spec|
        opex_spec : float, default=10
            |opex_spec|
        variable_costs : float, default=0,
            |variable_costs|
        lifetime : int, default=20
            |lifetime|

        Examples
        --------
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

        if efficiency_electricity_state_a + efficiency_heat_state_a > 1.0:
            raise ValueError("Total efficiency at state a is above 100%.")
        if efficiency_electricity_state_b + efficiency_heat_state_b > 1.0:
            raise ValueError("Total efficiency at state b is above 100%.")

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