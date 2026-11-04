from numpy.typing import ArrayLike

from oemof.eesyplan.project import Project
from oemof.eesyplan.type_checks import ct
from oemof.solph import Bus
from oemof.solph import Flow
from oemof.solph import Investment
from oemof.solph.components import GenericStorage


class EnergyStorage(GenericStorage):
    """
    Energy Storage System (ESS).

    This class represents a complete energy storage system for energy
    storage and dispatch.

    .. important ::
       This is a simplified representation of a complete ESS
       including all necessary components.

    Structure
    ---------
    *input*
        charge : Energy
    *output*
        discharge : Energy

    Parameters
    ----------
    name : string
        |name|
    project_data : Project object
        |project_data|

    bus_in : Bus
        |bus_in|
    bus_out : Bus | None, optional (default: None)
        |bus_out|
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
    variable_costs : float, optional (default: 0)
        |variable_costs|
    lifetime : int, optional (default: 20)
        |lifetime|
    soc_max : float, optional (default: 1)
        |soc_max|
    soc_min : float, optional (default: 0)
        |soc_min|
    loss_rate : float, optional (default: 0.0)
        |loss_rate|
    fixed_losses_relative : float, optional (default: 0.0)
        |fixed_losses_relative|
    fixed_losses_absolute : float, optional (default: 0.0)
        |fixed_losses_absolute|
    efficiency_charge : float, optional (default: 1.0)
        |efficiency_charge|
    efficiency_discharge : float, optional (default: 1.0)
        |efficiency_discharge|
    c_rate_charge : float, optional (default: 1.0)
        |c_rate_charge|
    c_rate_discharge : float, optional (default: None)
        |c_rate_discharge|
    initial_storage_level : float or None, optional (default: None)
        |initial_storage_level|
    end_storage_level : bool, optional (default: True)
        |end_storage_level|


    Examples
    --------
    >>> from oemof.eesyplan import Project
    >>> from oemof.eesyplan import CarrierBus
    >>> my_project = Project(
    ...         name="my_project",
    ...         economic_period=20,
    ...         tax=0,
    ...         discount_factor=0.01
    ...     )
    >>> heat_bus = CarrierBus(name="my_bus")
    >>> my_minimal_storage = EnergyStorage(
    ...     name="energy_storage",
    ...     project_data=my_project,
    ...     installed_capacity=10,
    ...     bus_in=heat_bus,
    ... )
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
    ... )
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
            capex_spec=ct(capex_spec),
            opex_spec=ct(opex_spec),
            lifetime=ct(lifetime),
            installed_capacity=ct(installed_capacity),
            maximum_capacity=ct(maximum_capacity),
        )
        if ct(c_rate_discharge) is None:
            c_rate_discharge = c_rate_charge

        self.c_rate_discharge = ct(c_rate_discharge)
        self.c_rate_charge = ct(c_rate_charge)

        self.efficiency_charge = ct(efficiency_charge)
        self.efficiency_discharge = ct(efficiency_discharge)
        self.age_installed = ct(age_installed)
        self.installed_capacity = ct(installed_capacity)
        self.capex_spec = ct(capex_spec)
        self.opex_spec = ct(opex_spec)
        self.initial_storage_level = ct(initial_storage_level)
        self.end_storage_level = ct(end_storage_level)

        if installed_capacity:
            self.capacity_charge = self.nv * self.c_rate_charge
            self.capacity_discharge = self.nv * self.c_rate_discharge
            self.c_rate_charge = None
            self.c_rate_discharge = None
        else:
            self.capacity_charge = Investment()
            self.capacity_discharge = Investment()

        if ct(bus_out) is None:
            bus_out = bus_in

        self.bus_out = ct(bus_out)
        self.bus_in = ct(bus_in)
        outputs = {
            self.bus_out: Flow(nominal_capacity=self.capacity_discharge)
        }
        self.variable_costs = ct(variable_costs)
        self.soc_min = ct(soc_min)
        self.soc_max = ct(soc_max)
        self.loss_rate = ct(loss_rate)
        self.fixed_losses_relative = ct(fixed_losses_relative)
        self.fixed_losses_absolute = ct(fixed_losses_absolute)
        self.initial_storage_level = ct(initial_storage_level)

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
