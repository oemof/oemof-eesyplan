from numpy.typing import ArrayLike

from oemof.eesyplan.project import Project
from oemof.solph import Bus
from oemof.solph import Flow
from oemof.solph.components import Source


class WindTurbine(Source):
    """
    Wind turbine for electricity generation.

    This class represents a wind turbine that converts kinetic
    energy of wind into electrical energy.

    .. important::
        This is a renewable energy source that contributes to the
        renewable share of the system.

    Optimisation:
        The characteristic quantity of the optimisation is the *nominal
        power-output* of the wind turbine given in kW.

    Args:
        name: |name|
        project_data: |project_data|
        bus_out_electricity: |bus_out_electricity|
        input_timeseries: |input_timeseries|
        age_installed: (optional) -- |age_installed|
        installed_capacity: (optional) -- |installed_capacity|
        maximum_capacity: (optional) -- |maximum_capacity|
        capex_spec: (optional) -- |capex_spec|
        opex_spec: (optional) -- |opex_spec|
        variable_costs: (optional) -- |variable_costs|
        lifetime: (optional) -- |lifetime|
        renewable_asset: (optional) -- |renewable_asset|

    Examples:
        >>> from oemof.eesyplan import Project
        >>> from oemof.eesyplan import CarrierBus
        >>> my_project = Project(
        ...         name="my_project",
        ...         economic_period=20,
        ...         tax=0,
        ...         discount_factor=0.01
        ...     )
        >>> el_bus = CarrierBus(name="my_electricity_bus")
        >>> my_wind = WindTurbine(
        ...     project_data=my_project,
        ...     bus_out_electricity=el_bus,
        ...     input_timeseries=[1,2,3],
        ...     name="my_wind_plant",
        ...     age_installed=0, # a
        ...     capex_spec=1000, # €/kW
        ...     opex_spec=10, # €/kW/a
        ...     variable_costs=0, # €/kWh
        ...     lifetime=25, # a
        ...     maximum_capacity=1000, # kW
        ...     renewable_asset=True,
        ... )
    """

    def __init__(
        self,
        project_data: Project,
        bus_out_electricity: Bus,
        input_timeseries: ArrayLike,
        name: str,
        age_installed: float | int = 0,
        installed_capacity: float | int | None = None,
        maximum_capacity: float | int | None = None,
        capex_spec: float | int = 1000,
        opex_spec: float | int | ArrayLike = 10,  # CHECK
        variable_costs: float | int | ArrayLike = 0,
        lifetime: float | int = 20,
        renewable_asset: bool = True,
    ):
        nv = project_data.create_invest_if_wanted(
            capex_spec=capex_spec,
            opex_spec=opex_spec,
            lifetime=lifetime,
            installed_capacity=installed_capacity,
            maximum_capacity=maximum_capacity,
        )

        self.bus_out_electricity = bus_out_electricity
        self.input_timeseries = input_timeseries
        self.name = name
        self.age_installed = age_installed
        self.installed_capacity = installed_capacity

        self.capex_spec = capex_spec
        self.opex_spec = opex_spec
        self.variable_costs = variable_costs
        self.lifetime = lifetime
        self.maximum_capacity = maximum_capacity
        self.renewable_asset = renewable_asset
        self.project_data = project_data

        outputs = {
            self.bus_out_electricity: Flow(
                fix=input_timeseries,
                nominal_capacity=nv,
                variable_costs=variable_costs,
            )
        }

        super().__init__(label=name, outputs=outputs)
