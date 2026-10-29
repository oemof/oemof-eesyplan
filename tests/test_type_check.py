import numpy as np
import pandas as pd
import pytest

from oemof.eesyplan.type_checks import check_parameter
from oemof.eesyplan.type_checks import to_array_or_number


class TestToArrayOrNumber:
    """Tests for to_array_or_number()."""

    @pytest.mark.parametrize("value", [0, 1, -17, 0.0, 3.5, -2.25])
    def test_numbers_are_returned_unchanged(self, value):
        """Numbers are returned unchanged, preserving object identity."""
        result = to_array_or_number(value)

        assert result is value
        assert isinstance(result, (int | float))

    def test_none_is_returned_unchanged(self):
        """None remains None."""
        assert to_array_or_number(None) is None

    @pytest.mark.parametrize(
        "value",
        [
            [1, 2, 3],
            (1.5, 2.5),
            [[1, 2], [3, 4]],
            np.array([1.0, 2.0]),
            pd.Series([1, 2, 3]),
        ],
    )
    def test_array_like_is_converted_to_ndarray(self, value):
        """Lists, tuples, Series and arrays are converted to NumPy arrays."""
        result = to_array_or_number(value)

        assert isinstance(result, np.ndarray)

    def test_values_are_preserved(self):
        """Values are preserved during conversion."""
        result = to_array_or_number([1, 2, 3])

        np.testing.assert_array_equal(result, np.array([1, 2, 3]))

    def test_nested_list_keeps_shape(self):
        """Multidimensional inputs retain their shape."""
        result = to_array_or_number([[1, 2, 3], [4, 5, 6]])

        assert result.shape == (2, 3)

    def test_zero_dim_array_stays_array(self):
        """A zero-dimensional array remains an array."""
        result = to_array_or_number(np.array(5))

        assert isinstance(result, np.ndarray)
        assert result.shape == ()

    def test_numpy_scalar_is_treated_as_number(self):
        """NumPy scalars are treated as numbers and are not converted."""
        result = to_array_or_number(np.float64(1.5))

        assert not isinstance(result, np.ndarray)
        assert result == 1.5


class TestCheckParameter:
    """Tests for check_parameter()."""

    @pytest.mark.parametrize(
        "values",
        [
            (0,),
            ("",),
            (False,),
            (0, "", [], {}),
            (np.nan,),
        ],
    )
    def test_values_pass(self, values):
        """All values except None are accepted."""
        assert check_parameter(*values) is None

    def test_no_arguments_pass(self):
        """There is nothing to check when no arguments are provided."""
        assert check_parameter() is None

    @pytest.mark.parametrize(
        "values",
        [
            (None,),
            (1, None),
            (None, "x"),
            (0, None, 2),
        ],
    )
    def test_none_raises(self, values):
        """None in any position raises a ValueError."""
        with pytest.raises(ValueError, match="None is not allowed."):
            check_parameter(*values)
