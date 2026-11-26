import pytest

from oemof.eesyplan import CarrierBus
from oemof.eesyplan import Electrolyzer
from oemof.eesyplan import Project
from oemof.solph import Investment


def test_error_message():
    el_bus_in = CarrierBus(name="Electricity")
    h2_bus_out = CarrierBus(name="H2-Bus")
    msg = (
        "Maximum capacity and installed capacity can't be set at the same time"
    )
    with pytest.raises(ValueError, match=msg):
        Electrolyzer(
            name="Electrolyzer",
            bus_in_electricity=el_bus_in,
            bus_out_hydrogen=h2_bus_out,
            age_installed=0,
            installed_capacity=1000,
            maximum_capacity=1000,
            capex_spec=1000,
            opex_spec=1000,
            lifetime=20,
            efficiency=0.9,
            variable_costs=0,
            project_data=Project(
                name="Project_X",
                economic_period=20,
                tax=0,
                discount_factor=0.01,
            ),
        )


@pytest.fixture
def project():
    return Project(name="p", tax=0, discount_factor=0.01, economic_period=20)


def test_no_maximum_returns_installed_capacity(project):
    assert project.create_invest_if_wanted(5, 100, 1, 20, None) == 5
    assert project.create_invest_if_wanted(None, 100, 1, 20, None) is None


def test_maximum_without_installed_creates_investment(project):
    result = project.create_invest_if_wanted(None, 234, 1, 20, 100)
    assert isinstance(result, Investment)
    assert result.existing == 0
    assert result.maximum == pytest.approx(100)


def test_maximum_and_installed_raises(project):
    with pytest.raises(ValueError, match="can't be set at the same time"):
        project.create_invest_if_wanted(5, 234, 1, 20, 100)
