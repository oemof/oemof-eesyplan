from numpy.typing import ArrayLike

from oemof.eesyplan.project import Project
from oemof.eesyplan.type_checks import normalise
from oemof.solph import Bus
from oemof.solph import Flow
from oemof.solph import Investment
from oemof.solph.components import GenericStorage


class EnergyStorage(GenericStorage):
    """
    Energy storage system.

    This component models a generic energy storage for storing and
    dispatching energy via a charge flow and a discharge flow. If bus_out
    is not given, the storage is connected to bus_in only, so charge and
    discharge share the same bus.

    .. important::
        This is a simplified representation of a complete energy storage
        system and does not cover every component such a system may
        comprise.

    Args:
        name: |name|
        project_data: |project_data|
        bus_in: |bus_in|
        bus_out: (optional) -- |bus_out|
        age_installed: (optional) -- |age_installed|
        installed_capacity: (optional) -- |installed_capacity|
        maximum_capacity: (optional) -- |maximum_capacity|
        capex_spec: (optional) -- |capex_spec|
        opex_spec: (optional) -- |opex_spec|
        variable_costs: (optional) -- |variable_costs|
        lifetime: (optional) -- |lifetime|
        soc_max: (optional) -- |soc_max|
        soc_min: (optional) -- |soc_min|
        loss_rate: (optional) -- |loss_rate|
        fixed_losses_relative: (optional) -- |fixed_losses_relative|
        fixed_losses_absolute: (optional) -- |fixed_losses_absolute|
        efficiency_charge: (optional) -- |efficiency_charge|
        efficiency_discharge: (optional) -- |efficiency_discharge|
        c_rate_charge: (optional) -- |c_rate_charge|
        c_rate_discharge: (optional) -- |c_rate_discharge|
        initial_storage_level: (optional) -- |initial_storage_level|
        end_storage_level: (optional) -- |end_storage_level|

    Examples:
        >>> from oemof.eesyplan import Project
        >>> from oemof.eesyplan import CarrierBus
        >>> my_project = Project(
        ...     name="my_project",
        ...     economic_period=20,
        ...     tax=0,
        ...     discount_factor=0.01,
        ...     )
        >>> heat_bus = CarrierBus(name="my_bus")
        >>> my_minimal_storage = EnergyStorage(
        ...     name="energy_storage",
        ...     project_data=my_project,
        ...     installed_capacity=10,
        ...     bus_in=heat_bus,
        ...     )
        >>> my_invest_storage = EnergyStorage(
        ...     name="energy_storage_extension",
        ...     bus_in=heat_bus,
        ...     bus_out=heat_bus,
        ...     age_installed=0,
        ...     maximum_capacity=1000,
        ...     capex_spec=3,
        ...     opex_spec=5,
        ...     variable_costs=0,
        ...     lifetime=10,
        ...     soc_max=1,
        ...     soc_min=0,
        ...     c_rate_charge=1,
        ...     c_rate_discharge=1,
        ...     efficiency_charge=0.99,
        ...     project_data=my_project,
        ...     loss_rate=0.6,
        ...     fixed_losses_relative=0.1,
        ...     )
    """

    def __init__(
        self,
        name: str,
        project_data: Project,
        bus_in: Bus,
        bus_out: Bus | None = None,
        age_installed: float | int = 0,
        installed_capacity: float | int | None = None,
        maximum_capacity: float | int | None = None,
        capex_spec: float | int = 0,
        opex_spec: float | int | ArrayLike = 0,  # CHECK: sequence ok?
        variable_costs: float | int | ArrayLike = 0,
        lifetime: float | int = 20,
        soc_max: float | int | ArrayLike = 1,  # CHECK: sequence ok?
        soc_min: float | int | ArrayLike = 0,  # CHECK: sequence ok?
        loss_rate: float | int | ArrayLike = 0.0,  # CHECK: sequence ok?
        fixed_losses_relative: float | int | ArrayLike = 0.0,  # CHECK
        fixed_losses_absolute: float | int | ArrayLike = 0.0,  # CHECK
        efficiency_charge: float | int | ArrayLike = 1.0,  # CHECK
        efficiency_discharge: float | int | ArrayLike = 1.0,  # CHECK
        c_rate_charge: float | int = 1.0,
        c_rate_discharge: float | int | None = None,
        initial_storage_level: float | int | None = None,
        end_storage_level: bool = True,
    ):
        self.name = name
        self.nv = project_data.create_invest_if_wanted(
            capex_spec=normalise(capex_spec),
            opex_spec=normalise(opex_spec),
            lifetime=normalise(lifetime),
            installed_capacity=normalise(installed_capacity),
            maximum_capacity=normalise(maximum_capacity),
        )
        if normalise(c_rate_discharge) is None:
            c_rate_discharge = c_rate_charge

        self.c_rate_discharge = normalise(c_rate_discharge)
        self.c_rate_charge = normalise(c_rate_charge)

        self.efficiency_charge = normalise(efficiency_charge)
        self.efficiency_discharge = normalise(efficiency_discharge)
        self.age_installed = normalise(age_installed)
        self.installed_capacity = normalise(installed_capacity)
        self.capex_spec = normalise(capex_spec)
        self.opex_spec = normalise(opex_spec)
        self.initial_storage_level = normalise(initial_storage_level)
        self.end_storage_level = end_storage_level

        if installed_capacity:
            self.capacity_charge = self.nv * self.c_rate_charge
            self.capacity_discharge = self.nv * self.c_rate_discharge
            self.c_rate_charge = None
            self.c_rate_discharge = None
        else:
            self.capacity_charge = Investment()
            self.capacity_discharge = Investment()

        if bus_out is None:
            bus_out = bus_in

        self.bus_out = bus_out
        self.bus_in = bus_in
        outputs = {
            self.bus_out: Flow(nominal_capacity=self.capacity_discharge)
        }
        self.variable_costs = normalise(variable_costs)
        self.soc_min = normalise(soc_min)
        self.soc_max = normalise(soc_max)
        self.loss_rate = normalise(loss_rate)
        self.fixed_losses_relative = normalise(fixed_losses_relative)
        self.fixed_losses_absolute = normalise(fixed_losses_absolute)
        self.initial_storage_level = normalise(initial_storage_level)

        super().__init__(
            label=self.name,
            nominal_capacity=self.nv,
            inputs={
                bus_in: Flow(
                    nominal_capacity=self.capacity_charge,
                    variable_costs=self.variable_costs,
                )
            },
            outputs=outputs,
            min_storage_level=self.soc_min,
            max_storage_level=self.soc_max,
            balanced=self.end_storage_level,
            initial_storage_level=self.initial_storage_level,
            inflow_conversion_factor=self.efficiency_charge,
            outflow_conversion_factor=self.efficiency_discharge,
            invest_relation_input_capacity=self.c_rate_charge,
            invest_relation_output_capacity=self.c_rate_discharge,
            loss_rate=self.loss_rate,
            fixed_losses_relative=self.fixed_losses_relative,
            fixed_losses_absolute=self.fixed_losses_absolute,
        )
