from numpy.typing import ArrayLike

from oemof.eesyplan.components.buses.carrier import Bus
from oemof.eesyplan.project import Project
from oemof.solph import Flow
from oemof.solph.components import Converter


class Electrolyzer(Converter):
    def __init__(
        self,
        name: str,
        bus_in_electricity: Bus,
        bus_out_hydrogen: Bus,
        project_data: Project,
        bus_out_heat: Bus | None = None,
        efficiency: float | int | ArrayLike = 0.3,  # CHECK
        # CHECK: sequence ok? Naming still open - originally flagged in
        # docstring as "TODO find a good attribute name"; description
        # text added in Pass 3, parameter name itself not decided yet.
        efficiency_heat: float | int | ArrayLike = 0.6,
        age_installed: float | int = 0,
        installed_capacity: float | int | None = None,
        maximum_capacity: float | int | None = None,
        capex_spec: float | int = 1000,
        opex_spec: float | int | ArrayLike = 10,  # CHECK
        variable_costs: float | int | ArrayLike = 0,
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
            |name|
        bus_in_electricity : Bus
            |bus_in_electricity|
        bus_out_hydrogen : Bus
            |bus_out_hydrogen|
        project_data : Project object
            |project_data|
        bus_out_heat : Bus or None, optional (default: None)
            |bus_out_heat|
        efficiency : float, optional (default: 0.3)
            |efficiency|
        efficiency_heat : float, optional (default: 0.6)
            |efficiency_heat|
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

        Examples
        --------

        >>> from oemof.eesyplan import Project
        >>> from oemof.eesyplan import Bus
        >>> el_bus_in = Bus(name="el_bus_in")
        >>> heat_bus_out = Bus(name="heat_bus_out")
        >>> h2_bus_out = Bus(name="h2_bus_out")
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
                # TODO BUG: bus_out_heat is optional (see "outputs" dict
                # above, which only adds bus_out_heat conditionally via
                # "if bus_out_heat is not None"). This conversion_factors
                # entry, however, is ALWAYS added, even when bus_out_heat
                # is None. Likely consequence: oemof.solph either raises
                # an error because a conversion factor is defined for a
                # bus that is not an input/output of this node, or (worse)
                # silently accepts it without effect - behaviour not yet
                # verified. Fix: wrap this entry in the same
                # "if bus_out_heat is not None" condition as "outputs"
                # above. Needs its
                # own dedicated bugfix commit with a regression test
                # (instantiate Electrolyzer with bus_out_heat=None and
                # verify no error / correct conversion_factors dict).
                bus_out_heat: efficiency_heat,
            },
        )
