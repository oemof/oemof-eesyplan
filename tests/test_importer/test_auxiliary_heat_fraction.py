import numpy as np
import pytest

from oemof.eesyplan.importer.auxiliary_heat_fraction import (
    calculate_fluid_mixture,
)
from oemof.eesyplan.importer.auxiliary_heat_fraction import (
    calculate_top_up_fraction,
)


class TestCalculateTopUpFraction:
    """Tests for calculate_top_up_fraction()."""

    def test_docstring_example(self):
        """The docstring example produces the expected values."""
        result = calculate_top_up_fraction(
            temperature_difference_source=[40, 40, 80],
            temperature_source=[60, 80, 140],
            temperature_supply=[80, 80, 80],
        )

        assert isinstance(result, np.ndarray)
        np.testing.assert_allclose(result, [1 / 3, 0.0, 0.0], atol=1e-12)

    def test_returned_values_are_fractions(self):
        """Results always lie within the range 0 <= x < 1."""
        result = calculate_top_up_fraction(
            temperature_difference_source=[10, 20, 30],
            temperature_source=[100, 5, 50],
            temperature_supply=[0, 25, 62],
        )

        assert np.all(result >= 0)
        assert np.all(result < 1)

    def test_negative_top_energy_is_clipped_to_zero(self):
        """A supply temperature below the source temperature gives 0."""
        result = calculate_top_up_fraction(
            temperature_difference_source=[40],
            temperature_source=[80],
            temperature_supply=[60],
        )

        np.testing.assert_allclose(result, [0.0])

    def test_fully_covered_by_top_up(self):
        """If the additional energy fully covers the difference, x = 2/3."""
        result = calculate_top_up_fraction(
            temperature_difference_source=[20],
            temperature_source=[60],
            temperature_supply=[100],
        )

        np.testing.assert_allclose(result, [2 / 3])

    @pytest.mark.parametrize("difference", [0, -1, -40.5])
    def test_non_positive_difference_raises(self, difference):
        """A non-positive source temperature difference is not allowed."""
        with pytest.raises(
            ValueError,
            match="Temperature difference of the source must be positive",
        ):
            calculate_top_up_fraction(
                temperature_difference_source=[difference],
                temperature_source=[60],
                temperature_supply=[80],
            )

    def test_single_invalid_step_is_enough_to_raise(self):
        """A single invalid time step is sufficient to raise an error."""
        with pytest.raises(
            ValueError,
            match="Temperature difference of the source must be positive",
        ):
            calculate_top_up_fraction(
                temperature_difference_source=[40, 40, 0],
                temperature_source=[60, 80, 140],
                temperature_supply=[80, 80, 80],
            )


class TestCalculateFluidMixture:
    """Tests for calculate_fluid_mixture()."""

    def test_docstring_example(self):
        """The docstring example produces the expected values."""
        result = calculate_fluid_mixture(
            temperature_difference_source=[20, 40, 60],
            temperature_difference_aux=[60, 60, 60],
            temperature_source=[60, 80, 100],
            temperature_supply=[80, 80, 80],
            temperature_aux=[100, 100, 101],
        )

        assert isinstance(result, np.ndarray)
        np.testing.assert_allclose(result, [0.75, 0.0, 0.0], atol=1e-12)

    def test_returned_values_are_fractions(self):
        """Results always lie within the range 0 <= x <= 1."""
        result = calculate_fluid_mixture(
            temperature_difference_source=[20, 30],
            temperature_difference_aux=[50, 50],
            temperature_source=[60, 70],
            temperature_supply=[70, 85],
            temperature_aux=[80, 90],
        )

        assert np.all(result >= 0)
        assert np.all(result <= 1)
        np.testing.assert_allclose(
            result, [0.7142857142857143, 0.8333333333333334]
        )

    def test_negative_fraction_is_clipped_to_zero(self):
        """Negative mixture fractions are set to 0."""
        result = calculate_fluid_mixture(
            temperature_difference_source=[60],
            temperature_difference_aux=[60],
            temperature_source=[100],
            temperature_supply=[80],
            temperature_aux=[101],
        )

        np.testing.assert_allclose(result, [0.0])

    @pytest.mark.parametrize(
        ("temperature_source", "temperature_aux"),
        [
            ([60, 60], [60, 80]),  # Equal temperatures
            ([80, 60], [60, 80]),  # Source warmer than auxiliary fluid
            ([60, 80], [80, 79]),  # Only one invalid time step
        ],
    )
    def test_aux_temperature_not_above_source_raises(
        self, temperature_source, temperature_aux
    ):
        """The auxiliary temperature must be strictly above the source."""
        with pytest.raises(
            ValueError,
            match="The auxiliary temperature must be above the source",
        ):
            calculate_fluid_mixture(
                temperature_difference_source=[20, 20],
                temperature_difference_aux=[60, 60],
                temperature_source=temperature_source,
                temperature_supply=[80, 80],
                temperature_aux=temperature_aux,
            )
