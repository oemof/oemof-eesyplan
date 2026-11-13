import json
import logging
from pathlib import Path

import pandas as pd
from datapackage import Package

from oemof.datapackage import datapackage  # noqa
from oemof.datapackage.resultpackage import read
from oemof.datapackage.resultpackage import write


def export_results(results, path, component_type_mapping=None):
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
        path = Path(str)
    write.export_results_to_datapackage(
        results=results, base_path=path, zip=False
    )
    logging.info(f"Exported results to {path.resolve()}")

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
                "description": "Name of the components of the energy system mapped to their type",
            }
        )

        package.save(path / "datapackage.json")


def import_results(path, es):
    results = read.import_results_from_resultpackage(path)
    groups = es.groups
    for key in results.keys():
        if isinstance(results[key], pd.DataFrame):
            results[key].rename(columns=groups, inplace=True)
    logging.info("Imported results")
    return results
