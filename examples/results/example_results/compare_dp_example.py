import warnings
from pathlib import Path

from oemof.tools.debugging import ExperimentalFeatureWarning

from oemof.eesyplan import ThermalStorage
from oemof.eesyplan import export_results
from oemof.eesyplan import import_results
from oemof.eesyplan.datapackage.energy_system import (
    create_energy_system_from_dp,
)
from oemof.eesyplan.model import optimise
from oemof.eesyplan.postprocessing import graphs
from oemof.eesyplan.postprocessing.KPIs import normalize_imported_results

warnings.filterwarnings("ignore", category=ExperimentalFeatureWarning)

# The scenario datapackages keep the older parameter names of the thermal
# storage. They are renamed here, the datapackages themselves stay
# unchanged.
LEGACY_NAMES = {
    ThermalStorage: {
        "thermal_losses_variable": "loss_rate",
        "thermal_losses_fixed": "fixed_losses_relative",
    },
}

SCENARIOS = {
    "Luft-Wärmepumpe und PV": "scenario_Luft-Wärmepumpe_und_PV",
    "Erd-Wärmepumpe und BHKW": "scenario_Erd-Wärmepumpe_und_BHKW",
}

EXAMPLE_PATH = Path(__file__).parent


def load_scenario(scenario_name):
    """Results and energy system of one scenario datapackage.

    The scenario is solved and exported first if no solved datapackage
    exists yet.
    """
    scenario_path = EXAMPLE_PATH / scenario_name
    es = create_energy_system_from_dp(
        scenario_path, attributemap=LEGACY_NAMES
    )
    results_path = scenario_path / "datapackage_solved"
    if not (results_path / "datapackage.json").exists():
        results = optimise(es)
        export_results(results, path=results_path)
    return import_results(path=results_path, es=es), es


if __name__ == "__main__":
    datasets = {}
    for name, scenario_name in SCENARIOS.items():
        results, es = load_scenario(scenario_name)
        normalize_imported_results(results)
        datasets[name] = (results, es)

    fig = graphs.compare_annual_costs(datasets)

    for name, (results, _es) in datasets.items():
        table = results["eesyplan"]["yearly_project_costs"]
        total = table.loc[table["component"] == "total", "total"].iloc[0]
        print(f"Total annual costs ({name}): {total:.2f} EUR")

    fig.show()
