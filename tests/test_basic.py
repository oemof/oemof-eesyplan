import pytest

from oemof.eesyplan.type_checks import check_parameter


def test_none_parameters():
    check_parameter(5, 6, 7)
    with pytest.raises(ValueError, match="None is not allowed"):
        check_parameter(5, 6, None)
