from numpy.typing import ArrayLike

from oemof.eesyplan.components.storages.storage import EnergyStorage
from oemof.eesyplan.project import Project
from oemof.solph import Bus


class HydrogenStorage(EnergyStorage):
    """
    Hydrogen energy storage system.

    This component models a hydrogen storage for storing and dispatching
    hydrogen via a charge flow and a discharge flow. If bus_out_hydrogen is
    not given, the storage is connected to bus_in_hydrogen only, so charge
    and discharge share the same bus.

    .. important::
        Storing hydrogen requires specialised storage technology to meet
        hydrogen handling and safety requirements.

    Args:
        name: |name|
        project_data: |project_data|
        bus_in_hydrogen: |bus_in_hydrogen|
        bus_out_hydrogen: (optional) -- |bus_out_hydrogen|
        installed_capacity: (optional) -- |installed_capacity|
        maximum_capacity: (optional) -- |maximum_capacity|
        capex_spec: (optional) -- |capex_spec|
        opex_spec: (optional) -- |opex_spec|
        variable_costs: (optional) -- |variable_costs|
        lifetime: (optional) -- |lifetime|
        age_installed: (optional) -- |age_installed|
        soc_max: (optional) -- |soc_max|
        soc_min: (optional) -- |soc_min|
        c_rate_charge: (optional) -- |c_rate_charge|
        c_rate_discharge: (optional) -- |c_rate_discharge|
        efficiency_charge: (optional) -- |efficiency_charge|
        efficiency_discharge: (optional) -- |efficiency_discharge|
        loss_rate: (optional) -- |loss_rate|

    Examples:
        >>> from oemof.eesyplan import Project
        >>> from oemof.eesyplan import CarrierBus
        >>> my_project = Project(
        ...     name="my_project",
        ...     economic_period=20,
        ...     tax=0,
        ...     discount_factor=0.01,
        ...     )
        >>> h2_bus = CarrierBus(name="my_h2_bus")
        >>> my_storage = HydrogenStorage(
        ...     name="hydrogen_storage_system",
        ...     project_data=my_project,
        ...     bus_in_hydrogen=h2_bus,
        ...     installed_capacity=10,
        ...     c_rate_charge=0.7,
        ...     c_rate_discharge=0.8,
        ...     loss_rate=0.0001,
        ...     )
        >>> my_invest_storage = HydrogenStorage(
        ...     name="hydrogen_storage_system_extension",
        ...     bus_in_hydrogen=h2_bus,
        ...     bus_out_hydrogen=h2_bus,
        ...     age_installed=0,
        ...     maximum_capacity=1000,
        ...     capex_spec=3,
        ...     opex_spec=5,
        ...     variable_costs=0,
        ...     lifetime=10,
        ...     soc_max=1,
        ...     soc_min=0,
        ...     c_rate_charge=0.7,
        ...     c_rate_discharge=0.8,
        ...     efficiency_charge=0.99,
        ...     project_data=my_project,
        ...     loss_rate=0.0001,
        ...     )
    """

    def __init__(
        self,
        name: str,
        project_data: Project,
        bus_in_hydrogen: Bus,
        bus_out_hydrogen: Bus | None = None,
        installed_capacity: float | int | None = None,
        maximum_capacity: float | int | None = None,
        capex_spec: float | int = 0,
        opex_spec: float | int | ArrayLike = 0,  # CHECK
        variable_costs: float | int | ArrayLike = 0,
        lifetime: float | int = 20,
        age_installed: float | int = 0,
        soc_max: float | int | ArrayLike = 1.0,  # CHECK
        soc_min: float | int | ArrayLike = 0,  # CHECK auf 0 gesetzt
        c_rate_charge: float | int = 1.0,
        c_rate_discharge: float | int | None = None,
        efficiency_charge: float | int | ArrayLike = 1.0,  # CHECK
        efficiency_discharge: float | int | ArrayLike = 1.0,  # CHECK
        loss_rate: float | int | ArrayLike = 0.0,  # CHECK
    ):
        super().__init__(
            name,
            project_data=project_data,
            installed_capacity=installed_capacity,
            bus_in=bus_in_hydrogen,
            bus_out=bus_out_hydrogen,
            age_installed=age_installed,
            capex_spec=capex_spec,
            opex_spec=opex_spec,
            variable_costs=variable_costs,
            lifetime=lifetime,
            soc_max=soc_max,
            soc_min=soc_min,
            loss_rate=loss_rate,
            efficiency_charge=efficiency_charge,
            efficiency_discharge=efficiency_discharge,
            c_rate_charge=c_rate_charge,
            c_rate_discharge=c_rate_discharge,
            maximum_capacity=maximum_capacity,
        )
