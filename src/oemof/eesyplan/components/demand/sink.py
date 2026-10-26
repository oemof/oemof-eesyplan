import numpy.typing as npt

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.eesyplan.project import Project
from oemof.solph import Flow
from oemof.solph.components import Sink as SolphSink


class Sink(SolphSink):
    def __init__(
        self,
        name: str,
        project_data: Project,
        bus_in: CarrierBus,
        age_installed: float | int = 0,
        installed_capacity: float | int | None = None,
        maximum_capacity: float | int | None = None,
        capex_spec: float | int = 1000,
        opex_spec: float | int | npt.ArrayLike = 10,  # CHECK
        variable_costs: float | int | npt.ArrayLike = 0,
        lifetime: float | int = 20,
        minimum: float | int | None = None,
        maximum: float | int | None = None,
        fix: float | int | npt.ArrayLike | None = None,
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

        Parameters
        ----------
        name : string
            |name|
        project_data : Project object
            |project_data|
        bus_in : oemof.eesyplan.CarrierBus
            |bus_in|
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
        minimum : float, optional
            |minimum|
        maximum : float, optional
            |maximum|
        fix: float | int | npt.ArrayLike, optional
            |fix|
        positive_gradient_limit : float, optional
            |positive_gradient_limit|
        negative_gradient_limit : float, optional
            |negative_gradient_limit|
        full_load_time_max : float, optional
            |full_load_time_max|
        full_load_time_min : float, optional
            |full_load_time_min|
        integer : bool, optional
            |integer|
        custom_properties_flow : dict, optional
            |custom_properties_flow|
        custom_properties : dict, optional
            |custom_properties|

        Examples
        --------
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
