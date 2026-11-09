import json

import oemof.eesyplan.postprocessing.graphs as graphs

def sankey_to_json(imported_results, row=None):
    fig, _ = graphs.sankey(
        imported_results["flow"], imported_results.energy_system, row=row
    )
    return json.loads(fig.to_json())

def timeseries_to_json(imported_results):
    fig = graphs.plot_timeseries(
        imported_results, imported_results.energy_system
    )
    print(json.loads(fig.to_json()))

    return json.loads(fig.to_json())

def capacities_to_json(imported_results):
    fig = graphs.capacities(
        imported_results, imported_results.energy_system
    )
    return json.loads(fig.to_json())

def energy_mix_to_json(imported_results):
    fig = graphs.plot_energy_mix(
        imported_results, imported_results.energy_system
    )
    return json.loads(fig.to_json())

def renewable_vs_nonrenewable_to_json(imported_results):
    fig = graphs.plot_renewable_vs_nonrenewable(
        imported_results, imported_results.energy_system
    )
    return json.loads(fig.to_json())

def annual_costs_to_json(imported_results):
    fig = graphs.plot_annual_costs(
        imported_results, imported_results.energy_system
    )
    print(json.loads(fig.to_json()))
    return json.loads(fig.to_json())

FIGURES = {
    "renewables": renewable_vs_nonrenewable_to_json,
    "costs": annual_costs_to_json,
    "sankey": sankey_to_json,
    "timeseries": timeseries_to_json,
    "energy_mix": energy_mix_to_json,
    "capacities": capacities_to_json,
}
