import logging
from pathlib import Path
from typing import Self

import pandas as pd

try:
    from pyproj import Transformer
except ModuleNotFoundError:

    class Transformer:
        def from_crs(self):
            pass

    logging.warning(
        "If you want to use the WeatherData importer of oemof-eesyplan, "
        "you have to install extra dependencies "
        "`pip install oemoef-eesyplan[importer]` "
    )


class WeatherData:
    """
    Container for TRY (Test Reference Year) weather data.

    This class holds meteorological data from German DWD (Deutscher
    Wetterdienst) Test Reference Year files. Attributes are initialized as
    None and populated via the `from_try_file` class method.

    Attributes:
        latitude: |latitude|
        longitude: |longitude|
        air_temperature_c: |air_temperature_c|
        air_pressure_hpa: |air_pressure_hpa|
        wind_direction_deg: |wind_direction_deg|
        wind_speed_ms: |wind_speed_ms|
        cloud_cover_oktas: |cloud_cover_oktas|
        water_vapor_gkg: |water_vapor_gkg|
        relative_humidity_percent: |relative_humidity_percent|
        direct_solar_wm2: |direct_solar_wm2|
        diffuse_solar_wm2: |diffuse_solar_wm2|
        atmospheric_radiation_wm2: |atmospheric_radiation_wm2|
        terrestrial_radiation_wm2: |terrestrial_radiation_wm2|
        quality_flag: |quality_flag|
    """

    def __init__(self):
        self.latitude: float | None = None
        self.longitude: float | None = None
        self.air_temperature_c: pd.Series | None = None
        self.air_pressure_hpa: pd.Series | None = None
        self.wind_direction_deg: pd.Series | None = None
        self.wind_speed_ms: pd.Series | None = None
        self.cloud_cover_oktas: pd.Series | None = None
        self.water_vapor_gkg: pd.Series | None = None
        self.relative_humidity_percent: pd.Series | None = None
        self.direct_solar_wm2: pd.Series | None = None
        self.diffuse_solar_wm2: pd.Series | None = None
        self.atmospheric_radiation_wm2: pd.Series | None = None
        self.terrestrial_radiation_wm2: pd.Series | None = None
        self.quality_flag: pd.Series | None = None

    def __len__(self):
        return len(self.air_temperature_c)

    def to_dict(self) -> dict[str, float | pd.Series | None]:
        """serialize to dictionary"""
        return {k: getattr(self, k) for k in self.__dict__}

    @classmethod
    def from_try_file(cls, file: Path | str) -> Self:
        """
        Create Weather Data object from TRY (Test Reference Year) file.

        Args:
            file: |file|

        """
        wd = cls()

        table = try_file2df(file)

        wd.longitude, wd.latitude = lon_lat_from_lambert(
            table["RW"].iloc[0], table["HW"].iloc[0]
        )

        wd.air_temperature_c = table["t"]
        wd.air_pressure_hpa = table["p"]
        wd.wind_direction_deg = table["WR"]
        wd.wind_speed_ms = table["WG"]
        wd.cloud_cover_oktas = table["N"]
        wd.water_vapor_gkg = table["x"]
        wd.relative_humidity_percent = table["RF"]
        wd.direct_solar_wm2 = table["B"]
        wd.diffuse_solar_wm2 = table["D"]
        wd.atmospheric_radiation_wm2 = table["A"]
        wd.terrestrial_radiation_wm2 = table["E"]
        wd.quality_flag = table["IL"]

        return wd


def lon_lat_from_lambert(
    right: float | int, height: float | int
) -> tuple[float | int, float | int]:
    """Convert Lambert coordinate system to longitude and latitude."""
    transformer = Transformer.from_crs(
        "EPSG:3034", "EPSG:4326", always_xy=True
    )
    return transformer.transform(right, height)


def try_file2df(file: Path | str) -> pd.DataFrame:
    """Convert TRY (Test Reference Year) text file to pandas.DataFrame."""
    return pd.read_csv(
        filepath_or_buffer=file, skiprows=32, delimiter=r"\s+"
    ).iloc[1:, :]
