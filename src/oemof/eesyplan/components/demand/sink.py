from numpy.typing import ArrayLike

from oemof.solph import Bus
from oemof.eesyplan.project import Project
from oemof.solph import Flow
from oemof.solph.components import Sink as SolphSink


class Sink(SolphSink):
    def __init__(
        self,
        name: str,
        project_data: Project,
        bus_in: Bus,
        age_installed: float | int = 0,
        installed_capacity: float | int | None = None,
        maximum_capacity: float | int | None = None,
        capex_spec: float | int = 1000,
        opex_spec: float | int | ArrayLike = 10,  # CHECK
        variable_costs: float | int | ArrayLike = 0,
        lifetime: float | int = 20,
        minimum: float | int | None = None,
        maximum: float | int | None = None,
        fix: float | int | ArrayLike | None = None,
        positive_gradient_limit: float | int | None = None,
        negative_gradient_limit: float | int | None = None,
        full_load_time_max: float | int | None = None,
        full_load_time_min: float | int | None = None,
        integer: bool = False,
        custom_properties_flow: dict | None = None,
        custom_properties: dict | None = None,
    ):
        """
        General Sink.

        Args:
            name: |name|
            project_data: |project_data|
            bus_in: |bus_in|
            age_installed: (optional) -- |age_installed|
            installed_capacity: (optional) -- |installed_capacity|
            maximum_capacity: (optional) -- |maximum_capacity|
            capex_spec: (optional) -- |capex_spec|
            opex_spec: (optional) -- |opex_spec|
            variable_costs: (optional) -- |variable_costs|
            lifetime: (optional) -- |lifetime|
            minimum: (optional) -- |minimum|
            maximum: (optional) -- |maximum|
            fix: (optional) -- |fix|
            positive_gradient_limit: (optional) -- |positive_gradient_limit|
            negative_gradient_limit: (optional) -- |negative_gradient_limit|
            full_load_time_max: (optional) -- |full_load_time_max|
            full_load_time_min: (optional) -- |full_load_time_min|
            integer: (optional) -- |integer|
            custom_properties_flow: (optional) -- |custom_properties_flow|
            custom_properties: (optional) -- |custom_properties|

        Examples:
            >>> from oemof.eesyplan import CarrierBus
            >>> from oemof.eesyplan import Project
            >>> bus = CarrierBus("Test", balanced=False)
            >>> project = Project(
            ...     name="Project_X",
            ...     economic_period=20,
            ...     tax=0,
            ...     discount_factor=0.01)
            >>> sink = Sink(
            ...     "test",
            ...     installed_capacity=10,
            ...     project_data=project,
            ...     bus_in=bus)
        """
        self.age_installed = age_installed

        nv = project_data.create_invest_if_wanted(
            capex_spec=capex_spec,
            opex_spec=opex_spec,
            lifetime=lifetime,
            installed_capacity=installed_capacity,
            maximum_capacity=maximum_capacity,
        )

        super().__init__(
            label=name,
            inputs={
                bus_in: Flow(
                    nominal_capacity=nv,
                    variable_costs=variable_costs,
                    minimum=minimum,
                    maximum=maximum,
                    fix=fix,
                    positive_gradient_limit=positive_gradient_limit,
                    negative_gradient_limit=negative_gradient_limit,
                    full_load_time_max=full_load_time_max,
                    full_load_time_min=full_load_time_min,
                    integer=integer,
                    custom_properties=custom_properties_flow,
                )
            },
            parent_node=None,
            custom_properties=custom_properties,
        )
