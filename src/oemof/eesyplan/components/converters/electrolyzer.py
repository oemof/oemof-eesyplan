import numpy.typing as npt

from oemof.eesyplan.components.buses.carrier import CarrierBus
from oemof.eesyplan.project import Project
from oemof.solph import Flow
from oemof.solph.components import Converter


class Electrolyzer(Converter):
    def __init__(
        self,
        name: str,
        bus_in_electricity: CarrierBus,
        bus_out_hydrogen: CarrierBus,
        project_data: Project,
        bus_out_heat: CarrierBus | None = None,
        efficiency: float | int | npt.ArrayLike = 0.3,  # CHECK
        efficiency_heat: float | int | npt.ArrayLike = 0.6,  # CHECK
        age_installed: float | int = 0,
        installed_capacity: float | int | None = None,
        maximum_capacity: float | int | None = None,
        capex_spec: float | int = 1000,
        opex_spec: float | int | npt.ArrayLike = 10,  # CHECK
        variable_costs: float | int | npt.ArrayLike = 0,
        lifetime: float | int = 20,
    ):
        """
        Electrolyzer for hydrogen production.

        This class represents an electrolyzer that converts electrical
        energy into hydrogen gas through electrolysis, producing both
        hydrogen and waste heat.

        .. important ::
            The efficiency parameter determines the conversion rate
            from electricity to hydrogen.

        Structure
        ---------
          *input*
            1. el_bus : Electricity
          *output*
            1. heat_bus : Heat
            2. h2_bus : H2

        Parameters
        ----------
        name : str
            Name of the asset.
        age_installed : int, default=0
            Number of years the asset has already been in operation.
        installed_capacity : float or None (default: None)
            |installed_capacity|
        maximum_capacity : float or None (default: None)
            |maximum_capacity|
        capex_spec : float, default=1000
            Specific investment costs of the asset related to the
            installed capacity (CAPEX).
        opex_spec : float, default=10
            Specific operational and maintenance costs of the asset
            related to the installed capacity (opex_spec).
        variable_costs : float, default=0.01
            Costs associated with a flow through/from the asset
            (variable_costs or fuel costs).
        lifetime : int, default=20
            Number of operational years of the asset until it has to
            be replaced.
        efficiency : float, default=0.8
            Ratio of energy output to energy input.
        efficiency_heat : float, default=0.6
            TODO find a good attribute name and description

        Examples
        --------

        >>> from oemof.eesyplan import Project
        >>> from oemof.eesyplan import CarrierBus
        >>> el_bus_in = CarrierBus(name="el_bus_in")
        >>> heat_bus_out = CarrierBus(name="heat_bus_out")
        >>> h2_bus_out = CarrierBus(name="h2_bus_out")
        >>> my_electrolyzer = Electrolyzer(
        ...     name="Electrolyzer",
        ...     bus_in_electricity=el_bus_in,
        ...     bus_out_heat=heat_bus_out,
        ...     bus_out_hydrogen=h2_bus_out,
        ...     age_installed=0,
        ...     maximum_capacity=1000,
        ...     capex_spec=1000,
        ...     opex_spec=1000,
        ...     lifetime=20,
        ...     efficiency=0.9,
        ...     efficiency_heat=0.1,
        ...     variable_costs=0,
        ...     project_data=Project(
        ...         name="Project_X", economic_period=20, tax=0,
        ...         discount_factor=0.01),
        ...     )
        >>> electrolyzer_no_heat = Electrolyzer(
        ...     name="Electrolyzer",
        ...     bus_in_electricity=el_bus_in,
        ...     bus_out_hydrogen=h2_bus_out,
        ...     age_installed=0,
        ...     maximum_capacity=1000,
        ...     capex_spec=1000,
        ...     opex_spec=1000,
        ...     lifetime=20,
        ...     efficiency=0.9,
        ...     variable_costs=0,
        ...     project_data=Project(
        ...         name="Project_X", economic_period=20, tax=0,
        ...         discount_factor=0.01),
        ...     )

        """
        nv = project_data.create_invest_if_wanted(
            capex_spec=capex_spec,
            opex_spec=opex_spec,
            lifetime=lifetime,
            installed_capacity=installed_capacity,
            maximum_capacity=maximum_capacity,
        )

        inputs = {bus_in_electricity: Flow()}

        outputs = {
            bus_out_hydrogen: Flow(
                nominal_capacity=nv,
                variable_costs=variable_costs,
            )
        }

        if bus_out_heat is not None:
            outputs[bus_out_heat] = Flow()

        self.name = name
        self.age_installed = age_installed
        self.installed_capacity = installed_capacity

        self.capex_spec = capex_spec
        self.opex_spec = opex_spec
        self.variable_costs = variable_costs
        self.lifetime = lifetime
        self.maximum_capacity = maximum_capacity
        self.efficiency = efficiency
        self.efficiency_heat = efficiency_heat
        super().__init__(
            label=name,
            outputs=outputs,
            inputs=inputs,
            conversion_factors={
                bus_out_hydrogen: efficiency,
                bus_out_heat: efficiency_heat,
            },
        )
