import numpy.typing as npt

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.eesyplan.project import Project
from oemof.solph import Flow
from oemof.solph.components import Converter


class AuxiliaryHeat(Converter):
    def __init__(
        self,
        name: str,
        bus_in_heat: CarrierBus,
        bus_in_heat_auxiliary: CarrierBus,
        bus_out_heat: CarrierBus,
        project_data: Project,
        auxiliary_heat_fraction: float | int | npt.ArrayLike,
        installed_capacity: float | int | None = None,
        maximum_capacity: float | int | None = None,
        age_installed: float | int = 0,
        capex_spec: float | int = 0,
        opex_spec: float | int | npt.ArrayLike = 0,  # CHECK
        variable_costs: float | int | npt.ArrayLike = 0,
        lifetime: float | int = 20,
    ):
        """
        This component can be used for heat sources whose temperature is too
        low for the target heat flow. Consequently, additional energy is
        required to heat the flow to the required temperature. By definition,
        the auxiliary flow must have at least the flow temperature.

        Parameters
        ----------
        name : string
            |name|
        bus_in_heat : CarrierBus
            |bus_in_heat|
        bus_in_heat_auxiliary : CarrierBus
            |bus_in_heat_auxiliary|
        bus_out_heat : CarrierBus
            |bus_out_heat|
        project_data : Project object
            |project_data|
        auxiliary_heat_fraction : float or int or npt.ArrayLike
            |auxiliary_heat_fraction|
        age_installed : float or int, optional (default: 0)
            |age_installed|
        installed_capacity : float or None (default: None)
            |installed_capacity|
        maximum_capacity : float or None (default: None)
            |maximum_capacity|
        capex_spec : float, optional (default: 0)
            |capex_spec|
        opex_spec : float, optional (default: 0)
            |opex_spec|
        variable_costs : float or array-like, optional (default: 0)
            |variable_costs|
        lifetime : int, optional (default: 20)
            |lifetime|

        Examples
        --------
        >>> import numpy as np
        >>> from oemof.eesyplan import Project
        >>> from oemof.eesyplan import CarrierBus
        >>> from oemof.eesyplan.importer.auxiliary_heat_fraction import (
        ...     calculate_top_up_fraction)
        >>> heat_bus = CarrierBus(name="heat_bus")
        >>> heat_bus_aux = CarrierBus(name="heat_bus_auxiliary")
        >>> heat_supply = CarrierBus(name="heat_supply")
        >>> heat_fraction = calculate_top_up_fraction(
        ...     temperature_difference_source=[40, 40, 40],
        ...     temperature_source=[60, 80, 100],
        ...     temperature_supply=[80, 80, 80],
        ... )
        >>> my_top_up_heater = AuxiliaryHeat(
        ...     name="top_heat",
        ...     bus_in_heat=heat_bus,
        ...     bus_in_heat_auxiliary=heat_bus_aux,
        ...     bus_out_heat=heat_supply,
        ...     project_data=Project(
        ...         name="Project_X", economic_period=20, tax=0,
        ...         discount_factor=0.01),
        ...     auxiliary_heat_fraction=heat_fraction,
        ...     installed_capacity=100,
        ...     )
        >>> np.round(my_top_up_heater.auxiliary_heat_fraction,2).tolist()
        [0.33, 0.0, 0.0]
        >>> cf = my_top_up_heater.conversion_factors
        >>> np.round(cf[heat_bus],2).tolist()
        [0.67, 1.0, 1.0]
        >>> np.round(cf[heat_bus_aux],2).tolist()
        [0.33, 0.0, 0.0]

        """
        self.name = name
        self.bus_in_heat = bus_in_heat
        self.bus_in_heat_auxiliary = bus_in_heat_auxiliary
        self.bus_out_heat = bus_out_heat
        self.project_data = project_data
        self.auxiliary_heat_fraction = auxiliary_heat_fraction
        self.installed_capacity = installed_capacity
        self.maximum_capacity = maximum_capacity
        self.age_installed = age_installed
        self.capex_spec = capex_spec
        self.opex_spec = opex_spec
        self.variable_costs = variable_costs
        self.lifetime = lifetime
        self.age_installed = age_installed

        nv = project_data.create_invest_if_wanted(
            capex_spec=capex_spec,
            opex_spec=opex_spec,
            lifetime=lifetime,
            installed_capacity=installed_capacity,
            maximum_capacity=maximum_capacity,
        )
        inputs = {
            bus_in_heat: Flow(),
            bus_in_heat_auxiliary: Flow(),
        }
        outputs = {
            bus_out_heat: Flow(
                nominal_capacity=nv,
                variable_costs=variable_costs,
            )
        }

        super().__init__(
            label=name,
            inputs=inputs,
            outputs=outputs,
            conversion_factors={
                bus_in_heat: 1 - self.auxiliary_heat_fraction,
                bus_in_heat_auxiliary: auxiliary_heat_fraction,
            },
        )
