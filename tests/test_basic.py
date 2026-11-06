from unittest.mock import Mock
from unittest.mock import patch

import pytest

from oemof.eesyplan import model
from oemof.eesyplan.type_checks import check_parameter


def test_results_init():
    with patch(
        "oemof.eesyplan.model.SolphResults.__init__", return_value=None
    ) as mock_base_init:
        instance = model.Results(object())
        assert isinstance(instance, model.Results)
        mock_base_init.assert_called_once()


def test_none_parameters():
    check_parameter(5, 6, 7)
    with pytest.raises(ValueError, match="None is not allowed"):
        check_parameter(5, 6, None)


def test_optimise_debug():
    with patch("oemof.eesyplan.model.Model") as mock_model_class:
        mock_model = mock_model_class.return_value
        mock_model.solve.return_value = "ok"
        result = model.optimise(Mock(), solver="cbc", debug=True)
        assert result == "ok"
        mock_model.solve.assert_called_once()
        _, kwargs = mock_model.solve.call_args
        assert kwargs["solve_kwargs"] == {"tee": True, "keepfiles": False}


def test_optimise_default():
    with patch("oemof.eesyplan.model.Model") as mock_model_class:
        mock_model = mock_model_class.return_value
        mock_model.solve.return_value = "ok"
        result = model.optimise(Mock())
        assert result == "ok"
        _, kwargs = mock_model.solve.call_args
        assert kwargs["solve_kwargs"] == {}
