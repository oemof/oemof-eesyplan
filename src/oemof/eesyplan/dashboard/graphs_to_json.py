import json

import oemof.eesyplan.postprocessing.graphs as graphs


def sankey_to_json(imported_results, row=None):
    fig, _ = graphs.sankey(
        imported_results["flow"], imported_results.energy_system, row=row
    )
    return json.loads(fig.to_json())
