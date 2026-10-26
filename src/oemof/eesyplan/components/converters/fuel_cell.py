import numpy.typing as npt

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.eesyplan.project import Project
from oemof.solph import Flow
from oemof.solph.components import Converter


class FuelCell(Converter):
    def __init__(
        self,
        name: str,
        bus_in_hydrogen: CarrierBus,
        bus_out_electricity: CarrierBus,
        age_installed: float | int = 0,
        installed_capacity: float | int | None = None,
        maximum_capacity: float | int | None = None,
        capex_spec: float | int = 1000,
        opex_spec: float | int | npt.ArrayLike = 10,  # CHECK
        variable_costs: float | int | npt.ArrayLike = 0,
        lifetime: float | int = 20,
        efficiency: float | int | npt.ArrayLike = 0.8,  # CHECK
        project_data: Project | None = None,  # CHECK: see Punkt D - project_data defaults to None but is used immediately below without a None-check
    ):
        """
        Fuel cell for electricity generation.

        This class represents a fuel cell that converts hydrogen or other
        fuels into electrical energy through electrochemical processes.

        .. important ::
            The efficiency of fuel cells is typically higher than
            combustion-based generators.

        Structure
        ---------
          *input*
            1. bus_in_hydrogen : H2
          *output*
            1. bus_out_electricity : Electricity

        Parameters
        ----------
        name : str
            |name|
        bus_in_hydrogen : CarrierBus
            |bus_in_hydrogen|
        bus_out_electricity : CarrierBus
            |bus_out_electricity|
        age_installed : float or int, optional (default: 0)
            |age_installed|
        installed_capacity : float or None (default: None)
            |installed_capacity|
        maximum_capacity : float or None (default: None)
            |maximum_capacity|
        capex_spec : float, optional (default: 1000)
            |capex_spec|
        opex_spec : float, optional (default: 10)
            |opex_spec|
        variable_costs : float, optional (default: 0)
            |variable_costs|
        lifetime : int, optional (default: 20)
            |lifetime|
        efficiency : float, optional (default: 0.8)
            |efficiency|
        project_data : Project object or None, optional (default: None)
            |project_data|

        Examples
        --------
        >>> from oemof.eesyplan import Project
        >>> from oemof.eesyplan import CarrierBus
        >>> h2_bus = CarrierBus(name="hydrogen_bus")
        >>> el_bus = CarrierBus(name="electricity_bus")
        >>> my_fuel_cell = FuelCell(
        ...     name="hydrogen_fuel_cell",
        ...     bus_in_hydrogen=h2_bus,
        ...     bus_out_electricity=el_bus,
        ...     age_installed=0,
        ...     maximum_capacity=1000,
        ...     capex_spec=1000,
        ...     opex_spec=1000,
        ...     lifetime=20,
        ...     efficiency=0.9,
        ...     variable_costs=0,
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

        inputs = {bus_in_hydrogen: Flow()}

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