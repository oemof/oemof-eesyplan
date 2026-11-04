import numpy as np
from numpy.typing import ArrayLike

from oemof.eesyplan.project import Project
from oemof.solph import Bus
from oemof.solph import Flow
from oemof.solph.components import Converter


class HeatPump(Converter):
    def __init__(
        self,
        name: str,
        project_data: Project,
        cop: float | int | ArrayLike,
        bus_in_electricity: Bus,
        bus_out_heat: Bus,
        bus_in_heat: Bus | None = None,
        installed_capacity: float | int | None = None,
        maximum_capacity: float | int | None = None,
        age_installed: float | int = 0,
        capex_spec: float | int = 0.0,
        variable_costs: float | int | ArrayLike = 0.0,
        opex_spec: float | int | ArrayLike = 0.0,  # CHECK
        lifetime: float | int = 20,
    ):
        """
        Heat pump for efficient heat generation.

        This class represents a heat pump that extracts heat from a
        low-temperature source and delivers it at a higher temperature
        using electrical energy.

        .. important::
            Heat pumps typically achieve efficiencies (COP) greater
            than 1.0, making them very efficient heating systems.

        Optimisation:
            The characteristic quantity of the optimisation is the
            *maximum heat power-output* of the heat pump given in kW.

        Args:
            name: |name|
            project_data: |project_data|
            cop: |cop|
            bus_in_electricity: |bus_in_electricity|
            bus_out_heat: |bus_out_heat|
            bus_in_heat: (optional) -- |bus_in_heat|
            installed_capacity: (optional) -- |installed_capacity|
            maximum_capacity: (optional) -- |maximum_capacity|
            age_installed: (optional) -- |age_installed|
            capex_spec: (optional) -- |capex_spec|
            variable_costs: (optional) -- |variable_costs|
            opex_spec: (optional) -- |opex_spec|
            lifetime: (optional) -- |lifetime|

        Examples:
            >>> from oemof.eesyplan import Project
            >>> from oemof.eesyplan import CarrierBus
            >>> el_bus = CarrierBus(name="electricity_bus")
            >>> ambient_heat_bus = CarrierBus(name="ambient_heat_bus")
            >>> heat_bus = CarrierBus(name="heat_bus")
            >>> my_heat_pump = HeatPump(
            ...     name="air_source_heat_pump",
            ...     bus_in_electricity=el_bus,
            ...     bus_out_heat=heat_bus,
            ...     installed_capacity=15,
            ...     cop=3.5,
            ...     project_data=Project(
            ...         name="Project_X", economic_period=20, tax=0,
            ...         discount_factor=0.01,
            ...     )
            ... )
            >>> my_heat_pump2 = HeatPump(
            ...     name="air_source_heat_pump",
            ...     bus_in_electricity=el_bus,
            ...     bus_in_heat=ambient_heat_bus,
            ...     bus_out_heat=heat_bus,
            ...     installed_capacity=15,
            ...     cop=[3.5] * 5,
            ...     project_data=Project(
            ...         name="Project_X", economic_period=20, tax=0,
            ...         discount_factor=0.01,
            ...     )
            ... )
        """

        if isinstance(cop, list):
            cop = np.array(cop)

        nv = project_data.create_invest_if_wanted(
            capex_spec=capex_spec,
            opex_spec=opex_spec,
            lifetime=lifetime,
            installed_capacity=installed_capacity,
            maximum_capacity=maximum_capacity,
        )

        inputs = {bus_in_electricity: Flow()}

        outputs = {
            bus_out_heat: Flow(
                nominal_capacity=nv,
                variable_costs=variable_costs,
            )
        }

        conversion_factors = {
            bus_in_electricity: 1 / cop,
        }

        if bus_in_heat is not None:
            conversion_factors[bus_in_heat] = (cop - 1) / cop
            inputs[bus_in_heat] = Flow()

        super().__init__(
            label=name,
            outputs=outputs,
            inputs=inputs,
            conversion_factors=conversion_factors,
        )

        self.name = name
        self.age_installed = age_installed
        self.installed_capacity = installed_capacity
        self.capex_spec = capex_spec
        self.variable_costs = variable_costs
        self.opex_spec = opex_spec
        self.lifetime = lifetime

        self.maximum_capacity = maximum_capacity
        self.cop = cop
