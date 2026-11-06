import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import pytest

from oemof.eesyplan.type_checks import (
    normalise,  # type: ignore[import-untyped]
)


class TestToArrayOrNumber:
    """Tests for to_array_or_number()."""

    @pytest.mark.parametrize("value", [0, 1, -17, 0.0, 3.5, -2.25])
    def test_numbers_are_returned_as_float(self, value):
        """Numbers are returned unchanged, preserving object identity."""
        result = normalise(value)

        assert result == float(value)
        assert isinstance(result, float)

    def test_none_is_returned_unchanged(self):
        """None remains None."""
        assert normalise(None) is None

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
        result = normalise(value)

        assert isinstance(result, np.ndarray)

    def test_values_are_preserved(self):
        """Values are preserved during conversion."""
        result = normalise([1, 2, 3])

        np.testing.assert_array_equal(result, np.array([1, 2, 3]))

    def test_nested_list_keeps_shape(self):
        """Multidimensional inputs retain their shape."""
        result = normalise([[1, 2, 3], [4, 5, 6]])

        assert result.shape == (2, 3)

    def test_zero_dim_array_stays_array(self):
        """A zero-dimensional array remains an array."""
        result = normalise(np.array(5))

        assert isinstance(result, float)
        assert result == 5.0

    def test_numpy_scalar_is_treated_as_number(self):
        """NumPy scalars are treated as numbers and are not converted."""
        result = normalise(np.float64(1.5))

        assert not isinstance(result, np.ndarray)
        assert result == 1.5
