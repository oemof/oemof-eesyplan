from pathlib import Path

import pandas as pd

from oemof.eesyplan.io import select_value
from oemof.eesyplan.io import unzip_package


def import_heat_demand_f_heat(path, network=None):
    temp_path = unzip_package(path)
    networks = {
        f.stem.split("_")[-1]: f for f in Path(temp_path.name).rglob("*.xlsx")
    }
    if network is None:
        network = select_value(list(networks.keys()))

    df = pd.read_excel(
        networks[network], sheet_name="Lastprofil", index_col=[0]
    )["Gesamtsumme"]
    temp_path.cleanup()
    return df
