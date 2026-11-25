import re

import pandas as pd
import pytest

from oemof.eesyplan.postprocessing import print_results as pr


class FakeResults(dict):
    """Dict-like stand-in for the oemof results object."""

    def __init__(self, data=None, timeindex=None):
        super().__init__(data or {})
        self.timeindex = timeindex


@pytest.fixture(autouse=True)
def simple_helpers(monkeypatch):
    monkeypatch.setattr(pr, "get_objective", lambda results: 12.5)
    monkeypatch.setattr(
        pr,
        "_solver_value",
        lambda results, key: "cbc" if key == "solver" else "optimal",
    )
    monkeypatch.setattr(
        pr, "edge_label", lambda column: (str(column[0]), str(column[1]))
    )
    monkeypatch.setattr(pr, "clean_label", str)


@pytest.fixture
def cost_table():
    return pd.DataFrame(
        {
            "Component": ["pv", "wind"],
            "Cost": [1234.5, float("nan")],
            "Other": [3.0, 4.0],
            "total": [1234.5, 4.0],
        }
    )


# --- _stored_kpis (line 35) --------------------------------------------


def test_stored_kpis_defaults_to_empty_dict():
    assert pr._stored_kpis(FakeResults()) == {}


def test_stored_kpis_attribute_fallback():
    results = FakeResults()
    setattr(results, pr.EESYPLAN_KEY, {"lcoe": 1.0})
    assert pr._stored_kpis(results) == {"lcoe": 1.0}


def test_stored_kpis_data_fallback():
    results = FakeResults()
    results._data = {pr.EESYPLAN_KEY: {"lcoe": 2.0}}
    assert pr._stored_kpis(results) == {"lcoe": 2.0}


# --- _print_result_structure (lines 72-73, 77) --------------------------


def test_print_result_structure_kind_of_each_key(capsys):
    index = pd.date_range("2023-01-01", periods=3, freq="h")
    results = FakeResults(
        {
            "scalar": 3.5,
            "ts": pd.DataFrame({"a": [1, 2, 3]}, index=index),
            "element": pd.DataFrame({"a": [1]}),
            "empty": pd.DataFrame(),
        },
        timeindex=index,
    )

    pr._print_result_structure(results)

    rows = {
        line.split()[0]: line.split()
        for line in capsys.readouterr().out.splitlines()
        if line.strip()
    }
    assert rows["scalar"][1] == "float"
    assert rows["ts"][1:3] == ["time", "series"]
    assert rows["element"][1] == "element"
    assert rows["empty"][1] == "empty"


# --- _print_kpis (lines 93-103, 104->106) -------------------------------


def test_print_kpis_formats_values_and_skips_tables(capsys):
    kpis = {
        "lcoe": 0.123456789,
        "n_nodes": 3,
        "solver": "cbc",
        "lcoe_considered_flows": [("grid", "bus")],
        "table": pd.DataFrame({"a": [1]}),
    }

    pr._print_kpis(FakeResults({pr.EESYPLAN_KEY: kpis}))

    out = capsys.readouterr().out
    assert "0.123457" in out
    assert "3.000000" in out
    assert "cbc" in out
    assert re.search(r"grid\s+->\s+bus", out)
    assert "table" not in out
    assert "none calculated" not in out


def test_print_kpis_only_tables_prints_hint(capsys):
    kpis = {"table": pd.DataFrame({"a": [1]})}

    pr._print_kpis(FakeResults({pr.EESYPLAN_KEY: kpis}))

    assert "none calculated" in capsys.readouterr().out


# --- _print_investments (149->exit, 156->155) ---------------------------


def test_print_investments_without_investment_costs(capsys):
    results = FakeResults(
        {"invest": pd.DataFrame([[1.5, 0.0]], columns=["pv", "wind"])}
    )

    pr._print_investments(results)

    out = capsys.readouterr().out
    assert "pv" in out
    assert "wind" not in out  # zero capacities are skipped
    assert "Annual equivalent" not in out


def test_print_investments_with_investment_costs(capsys):
    results = FakeResults(
        {
            "invest": pd.DataFrame([[1.5, 0.0]], columns=["pv", "wind"]),
            "investment_costs": pd.DataFrame(
                [[0.0, 2.0]], columns=["pv", "wind"]
            ),
        }
    )

    pr._print_investments(results)

    invest_part, costs_part = capsys.readouterr().out.split(
        "Annual equivalent periodical costs"
    )
    assert "pv" in invest_part
    assert "wind" not in invest_part
    assert "wind" in costs_part
    assert "pv" not in costs_part  # zero costs are skipped


# --- _as_float / _format_cost (line 183) --------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, None),  # bool is not a number here
        (False, None),
        (None, None),
        ("abc", None),
        (float("nan"), None),
        (float("inf"), None),
        (3, 3.0),
        ("1.5", 1.5),
    ],
)
def test_as_float(value, expected):
    assert pr._as_float(value) == expected


def test_format_cost():
    assert pr._format_cost(1234.5, 12) == "    1 234.50"
    assert pr._format_cost(None, 5) == "    -"


# --- _print_cost_table (201->207) ---------------------------------------


def test_print_cost_table_with_explicit_columns(capsys, cost_table):
    pr._print_cost_table(cost_table, value_columns=["Cost"], title="T")

    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "T"
    assert "Cost" in lines[1]
    assert "total" in lines[1]
    assert "Other" not in "\n".join(lines)
    assert lines[1].index("Cost") < lines[1].index("total")
    assert "1 234.50" in lines[3]
    assert lines[4].split()[-2] == "-"  # NaN falls back to a dash


def test_print_cost_table_default_columns(capsys, cost_table):
    pr._print_cost_table(cost_table)

    header = capsys.readouterr().out.splitlines()[0]
    assert "Cost" in header
    assert "Other" in header


# --- _print_kpi_tables (lines 230, 234) ---------------------------------


def test_print_kpi_tables_prints_both_tables(capsys, cost_table):
    kpis = {
        "yearly_project_costs": cost_table,
        "project_cost_table": cost_table,
    }

    pr._print_kpi_tables(FakeResults({pr.EESYPLAN_KEY: kpis}))

    out = capsys.readouterr().out
    assert "Yearly project costs:" in out
    assert "Project costs:" in out


def test_print_kpi_tables_without_tables_prints_nothing(capsys):
    pr._print_kpi_tables(FakeResults({pr.EESYPLAN_KEY: {}}))

    assert capsys.readouterr().out == ""
