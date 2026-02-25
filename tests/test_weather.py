from pathlib import Path

from oemof.eesyplan.importer import weather_data


def test_weather_file_import():
    """The import of the test weather file failed."""
    path = Path(
        Path(__file__).parent, "test_data", "TRY2015_39065002972500_Jahr.dat"
    )
    w_obj = weather_data.WeatherData.from_try_file(path)
    assert round(w_obj.air_temperature_c.mean(), 3) == 9.921
    assert len(w_obj) == 8760
    assert round(w_obj.to_dict()["air_temperature_c"].mean(), 3) == 9.921
