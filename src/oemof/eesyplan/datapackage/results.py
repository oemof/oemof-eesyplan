import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from datapackage import Package

from oemof.datapackage import datapackage  # noqa
from oemof.datapackage.resultpackage import read
from oemof.datapackage.resultpackage import write


def export_results(results, path, component_type_mapping=None, zip=False):
    # ToDo The following lines are neccessary until the bug is fixed in solph
    for key in results.keys():
        if key in ["Solver", "Problem", "Solution"]:
            continue
        try:
            results[key]
        except KeyError:
            results._variables.pop(key, None)  # not all keys are variables
    # ToDo End of temporary fix

    if isinstance(path, str):
        path = Path(path)

    write.export_results_to_datapackage(
        results=results, base_path=path, zip=zip
    )
    logging.info(f"Exported results to {path.resolve()}")

    # TODO add this as results key in the future (NB one need to modify
    #  export_results_to_datapackage
    #  to allow exporting json format
    if isinstance(component_type_mapping, dict):
        results_root = path / "results"
        key = "component_type_mapping"
        fname = f"{key}.json"
        fpath = results_root / fname
        fpath.touch()

        with fpath.open(
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                component_type_mapping,
                f,
                indent=4,
            )

        package = Package(str(path / "datapackage.json"))
        package.add_resource(
            {
                "name": key,
                "path": f"results/{fname}",
                "format": "json",
                "kind": "typemap",
                "description": "Name of the components of the energy system "
                "mapped to their type",
            }
        )

        # TODO Start fix of variable_costs, remove when fixed in solph
        df_opex = pd.DataFrame(index=results._model.es.timeindex[:-1])

        try:
            flow_values = results["flow"]
        except KeyError:  # no flows
            return pd.DataFrame()

        for i, o in flow_values.columns:
            # access the variable costs of each flow
            variable_costs = results._model.flows[i, o].variable_costs

            if isinstance(variable_costs, np.ndarray):
                # map flows and variable costs and multiply
                df_opex[(i, o)] = flow_values[(i, o)] * variable_costs
            else:
                df_opex[(i, o)] = variable_costs * flow_values[(i, o)]

        df_opex = df_opex.reset_index(drop=True)
        df_opex.index.name = "index"
        df_opex.columns = pd.MultiIndex.from_tuples(
            df_opex.columns, names=["from", "to"]
        )

        res = package.get_resource("variable_costs")
        out_csv = path / res.descriptor["path"]
        df_opex.to_csv(out_csv)
        # TODO End fix of variable_costs, remove when fixed in solph

        package.save(path / "datapackage.json")


def import_results(path, es):
    results = read.import_results_from_resultpackage(path)
    groups = es.groups
    for key in results.keys():
        if isinstance(results[key], pd.DataFrame):
            results[key].rename(columns=groups, inplace=True)
    logging.info("Imported results")
    return results
