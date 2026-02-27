import warnings
import logging
from pathlib import Path

from oemof.datapackage import datapackage  # noqa
from oemof.eesyplan.typemap import TYPEMAP
from oemof.network import graph
from oemof.solph import Model
from oemof.solph import EnergySystem
from oemof.solph import Results
from oemof.tools.debugging import ExperimentalFeatureWarning
from oemof.visio import ESGraphRenderer

warnings.filterwarnings("ignore", category=ExperimentalFeatureWarning)


def create_energy_system_from_dp(
    scenario_dir, results_path=None, scenario_name="scenario", plot=None
):
    # results_path = Path(Path.home(), "oemof-eesyplan", "results")
    # scenario_dir = "openPlan_package"
    # plot = "graph"  # "graph", "visio", None

    if scenario_dir.is_dir():
        scenario_dir = scenario_dir / "datapackage.json"

    # create energy system object from the datapackage
    es = EnergySystem.from_datapackage(
        scenario_dir,  # Path(scenario_dir, "datapackage.json"),
        attributemap={},
        typemap=TYPEMAP,  # TODO load the typemap from information within the datapackage
    )

    if results_path is not None:
        Path.mkdir(results_path, parents=True, exist_ok=True)
        if plot == "graph":
            graph.create_nx_graph(
                es, filename=Path(results_path, "test_graph.graphml")
            )
        elif plot == "visio":
            energy_system_graph = Path(
                results_path, f"{scenario_name}_energy_system.png"
            )

            es_graph = ESGraphRenderer(
                es,
                legend=False,
                filepath=str(energy_system_graph),
                img_format="png",
            )
            es_graph.render()
    return es

def optimise(energy_system, solver="cbc", debug=False):
    """Optimise the energy system."""
    logging.info("Create model")
    optimization_model = Model(energysystem=energy_system)

    # solve problem
    logging.info("Solve model")

    if debug:
        skwargs = {"tee": True, "keepfiles": False}
    else:
        skwargs = {}
    optimization_model.solve(solver=solver, solve_kwargs=skwargs)
    return Results(optimization_model)
