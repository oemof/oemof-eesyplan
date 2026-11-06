from numpy.typing import ArrayLike

from oemof.eesyplan.components.storages.storage import EnergyStorage
from oemof.eesyplan.project import Project
from oemof.solph import Bus


class ThermalStorage(EnergyStorage):
    """
    Thermal energy storage system.

    This component models a thermal storage for storing and dispatching
    heat via a charge flow and a discharge flow. If bus_out_heat is not
    given, the storage is connected to bus_in_heat only, so charge and
    discharge share the same bus.

    .. important::
        This is a simplified representation of a complete thermal energy
        storage system and does not cover every component such a system may
        comprise.

    Args:
        name: |name|
        project_data: |project_data|
        bus_in_heat: |bus_in_heat|
        bus_out_heat: (optional) -- |bus_out_heat|
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
        >>> heat_bus = CarrierBus(name="my_heat_bus")
        >>> my_storage = ThermalStorage(
        ...     name="thermal_storage",
        ...     project_data=my_project,
        ...     bus_in_heat=heat_bus,
        ...     installed_capacity=10,
        ...     )
        >>> my_invest_storage = ThermalStorage(
        ...     name="thermal_storage_extension",
        ...     bus_in_heat=heat_bus,
        ...     bus_out_heat=heat_bus,
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
        ...     loss_rate=0.06,
        ...     fixed_losses_relative=0.02,
        ...     )
    """

    def __init__(
        self,
        name: str,
        project_data: Project,
        bus_in_heat: Bus,
        bus_out_heat: Bus | None = None,
        age_installed: float | int = 0,
        installed_capacity: float | int | None = None,
        maximum_capacity: float | int | None = None,
        capex_spec: float | int = 0.0,
        opex_spec: float | int | ArrayLike = 0.0,  # CHECK
        variable_costs: float | int | ArrayLike = 0.0,
        lifetime: float | int = 20,
        soc_max: float | int | ArrayLike = 1.0,  # CHECK
        soc_min: float | int | ArrayLike = 0.0,  # CHECK
        loss_rate: float | int | ArrayLike = 0.0,  # CHECK
        fixed_losses_relative: float | int | ArrayLike = 0.0,  # CHECK
        fixed_losses_absolute: float | int | ArrayLike = 0.0,  # CHECK
        efficiency_charge: float | int | ArrayLike = 1.0,  # CHECK
        efficiency_discharge: float | int | ArrayLike = 1.0,  # CHECK
        c_rate_charge: float | int = 1.0,
        c_rate_discharge: float | int | None = None,
        initial_storage_level: float | int | None = None,
        end_storage_level: bool = True,
    ):
        super().__init__(
            name,
            project_data=project_data,
            installed_capacity=installed_capacity,
            maximum_capacity=maximum_capacity,
            bus_in=bus_in_heat,
            bus_out=bus_out_heat,
            age_installed=age_installed,
            capex_spec=capex_spec,
            opex_spec=opex_spec,
            variable_costs=variable_costs,
            lifetime=lifetime,
            soc_max=soc_max,
            soc_min=soc_min,
            loss_rate=loss_rate,
            fixed_losses_relative=fixed_losses_relative,
            fixed_losses_absolute=fixed_losses_absolute,
            efficiency_charge=efficiency_charge,
            efficiency_discharge=efficiency_discharge,
            c_rate_charge=c_rate_charge,
            c_rate_discharge=c_rate_discharge,
            initial_storage_level=initial_storage_level,
            end_storage_level=end_storage_level,
        )
