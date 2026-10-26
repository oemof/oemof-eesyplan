import numpy.typing as npt

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.eesyplan.project import Project
from oemof.solph import Flow
from oemof.solph.components import Converter


class ChpFixedRatio(Converter):
    def __init__(
        self,
        name: str,
        bus_in_fuel: CarrierBus,
        bus_out_electricity: CarrierBus,
        bus_out_heat: CarrierBus,
        efficiency_electricity_chp: float | int | npt.ArrayLike,
        efficiency_heat_chp: float | int | npt.ArrayLike,
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
        Combined Heat and Power plant with fixed heat-to-power ratio.

        This class represents a CHP plant that operates with a fixed
        ratio between heat and electricity generation, providing less
        operational flexibility but simpler control.

        .. important ::
            The fixed ratio constraint limits operational flexibility
            but ensures consistent heat-to-power ratios.

        Structure
        ---------
          *input*
            1. fuel : Fuel
          *output*
            1. heat_bus : Heat
            2. electricity_bus : Electricity

        Optimisation
          The characteristic quantity of the optimization is the
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
        efficiency_electricity_chp : float
            |efficiency_electricity_chp|
        efficiency_heat_chp : float
            |efficiency_heat_chp|
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
        >>> my_chp_fixed = ChpFixedRatio(
        ...     name="fixed_ratio_chp",
        ...     bus_in_fuel=fuel_bus,
        ...     bus_out_heat=heat_bus,
        ...     bus_out_electricity=el_bus,
        ...     maximum_capacity=1000,
        ...     efficiency_electricity_chp=0.3,
        ...     efficiency_heat_chp=0.5,
        ...     capex_spec=1500,
        ...     opex_spec=15,
        ...     lifetime=20,
        ...     project_data=Project(
        ...         name="Project_X", economic_period=20, tax=0,
        ...         discount_factor=0.01,
        ...     )
        ... )

        """

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

        conversion_factors = {
            bus_out_electricity: efficiency_electricity_chp,
            bus_out_heat: efficiency_heat_chp,
        }

        self.age_installed = age_installed
        self.installed_capacity = installed_capacity
        self.capex_spec = capex_spec
        self.opex_spec = opex_spec
        self.variable_costs = variable_costs
        self.lifetime = lifetime

        self.maximum_capacity = maximum_capacity
        self.efficiency_electricity_chp = efficiency_electricity_chp
        self.efficiency_heat_chp = efficiency_heat_chp
        super().__init__(
            label=name,
            outputs=outputs,
            inputs=inputs,
            conversion_factors=conversion_factors,
        )
