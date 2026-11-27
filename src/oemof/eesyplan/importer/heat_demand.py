import datetime
from pathlib import Path

import pandas as pd
from numpy.typing import ArrayLike
from oemof.demand import bdew

from oemof.eesyplan.gui import select_value
from oemof.eesyplan.io import unzip_package


PROFILE_TYPES_HEAT_BDEW = {
    "EFH": "Single-family house",
    "MFH": "Apartment building",
    "GHD": "Commerce/Services general",
    "GMF": "Household-like business enterprises",
    "GGA": "Restaurants",
    "GHA": "Retail and wholesale",
    "GMK": "Metal and automotive",
    "GBH": "Accommodation",
    "GKO": "Local authorities, credit institutions and insurancecompanies",
    "GBD": "Other operational services",
    "GWA": "Laundries, dry cleaning",
    "GGB": "Horticulture",
    "GBA": "Bakery",
    "GPD": "Paper and printing",
}


def import_heat_demand_f_heat(file, network=None):
    """Import f-heat heat demand from zip-file."""
    temp_path = unzip_package(file)
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


def create_heat_demand(
    outdoor_temperature: ArrayLike,
    profile_type: str,
    annual_heat_demand: float|int,
    building_year: int,
    wind_class: str ="not windy",
    # todo: add a function to "restore variability or randomness to a profile"
):
    """
    Function to create a BDEW - standardized heat load profile based on the
    outside air temperature, building parameters and total heat demand.

    The BDEW standard heating profiles are based on a large set of measured
    data averaged into a single load time series, which makes them suitable for
    aggregated demand studies but not ideal for simulating individual building
    peaks.

    Args:
        outdoor_temperature: |outdoor_temperature|
        profile_type: |profile_type|
        annual_heat_demand: |annual_heat_demand|
        building_year: |building_year|
        wind_class: |wind_class|
        building_year: |building_year|
        wind_class: |wind_class|

    Example:
        >>> from oemof.demand import bdew
        >>> heat_demand = create_heat_demand(
        ...     outdoor_temperature=[3] * 8760,
        ...     profile_type="Single-family house",
        ...     annual_heat_demand=231,
        ...     building_year=1992,
        ...     wind_class="Not windy",)
    """

    # todo: get time from project
    times = pd.date_range(
        "2021-01-01 0:00", "2021-12-31 23:00", freq="1h", tz="Europe/Berlin"
    )

    match wind_class:
        case "Not windy":
            wind_class = 0
        case "Windy":
            wind_class = 1
        case _:  # pragma: no cover
            pass

    building_class = 0

    if profile_type in ("Single-family house", "Apartment building", "EFH",
                        "MFH"):
        match building_year:
            case y if y <= 1918:
                building_class = 1
            case y if 1919 <= y <= 1948:
                building_class = 2
            case y if 1949 <= y <= 1957:
                building_class = 3
            case y if 1958 <= y <= 1968:
                building_class = 4
            case y if 1969 <= y <= 1978:
                building_class = 5
            case y if 1979 <= y <= 1983:
                building_class = 6
            case y if 1984 <= y <= 1994:
                building_class = 7
            case y if 1995 <= y <= 1999:
                building_class = 8
            case y if 2000 <= y <= 2006:
                building_class = 9
            case y if 2007 <= y <= 2010:
                building_class = 10
            case y if y >= 2011:
                building_class = 11

    match profile_type:
        case "Single-family house":
            profile_type = "EFH"
        case "Apartment building":
            profile_type = "MFH"
        case "Commerce/Services general":
            profile_type = "GHD"
        case "Restaurants":
            profile_type = "GGA"
        case "Retail and wholesale":
            profile_type = "GBH"
        case "Metal and automotive":
            profile_type = "GMK"
        case "Household-like business enterprises":
            profile_type = "GMF"
        case "Accommodation":
            profile_type = "GBH"
        case "Local authorities, credit institutions and insurancecompanies":
            profile_type = "GKO"
        case "Other operational services":
            profile_type = "GBD"
        case "Laundries, dry cleaning":
            profile_type = "GWA"
        case "Horticulture":
            profile_type = "GGB"
        case "Bakery":
            profile_type = "GBA"
        case "Paper and printing":
            profile_type = "GPD"
        case _ if profile_type in PROFILE_TYPES_HEAT_BDEW.keys():
            pass
        case _:  # pragma: no cover
            return "Unknown value"

    # ToDo: https://github.com/workalendar/workalendar
    #  This package could be an optional dependency:
    #  pip install oemof-eesyplan[importer]
    holidays = {
        datetime.date(times[0].year, 1, 1): "New year",
        datetime.date(times[0].year, 5, 1): "Labour Day",
        datetime.date(times[0].year, 10, 3): "Day of German Unity",
        datetime.date(times[0].year, 12, 25): "Christmas Day",
        datetime.date(times[0].year, 12, 26): "Second Christmas Day",
    }

    demand_profile = bdew.HeatBuilding(
        times,
        holidays=holidays,
        temperature=pd.Series(outdoor_temperature),
        shlp_type=profile_type,
        building_class=building_class,
        wind_class=wind_class,
        annual_heat_demand=annual_heat_demand,
        name="",
    ).get_bdew_profile()

    return demand_profile
