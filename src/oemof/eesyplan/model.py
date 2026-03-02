import logging

from oemof.solph import Model
from oemof.solph import Results


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
