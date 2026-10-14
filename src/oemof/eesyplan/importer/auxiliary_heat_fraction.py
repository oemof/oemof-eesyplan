import numpy as np
from numpy.typing import ArrayLike


def calculate_top_up_fraction(
    temperature_difference_source: float | int | ArrayLike,
    temperature_source: float | int | ArrayLike,
    temperature_supply: float | int | ArrayLike,
):
    """
    Calculate the top_up fraction of the temperature difference source.

    Parameters
    ----------
    temperature_difference_source
    temperature_source
    temperature_supply

    Returns
    -------

    Examples
    --------
    >>> a=5
    >>> top_frac = calculate_top_up_fraction(
    ...     temperature_difference_source=[40, 40, 80],
    ...     temperature_source=[60, 80, 140],
    ...     temperature_supply=[80, 80, 80],
    ... )
    >>> [round(float(t), 2) for t in top_frac]
    [0.33, 0.0, 0.0]

    """
    temperature_supply = np.array(temperature_supply)
    temperature_source = np.array(temperature_source)
    temperature_difference_source = np.array(temperature_difference_source)

    if any(temperature_difference_source <= 0):
        msg = "Temperature difference of the source must be positive"
        raise ValueError(msg)

    top_energy_per_unit = (temperature_supply - temperature_source) / (
        temperature_difference_source
    )
    top_energy_per_unit[top_energy_per_unit < 0] = 0
    top_up_fraction = top_energy_per_unit / (top_energy_per_unit + 1)

    return top_up_fraction


def calculate_fluid_mixture(
    temperature_supply: float | int | ArrayLike,
    temperature_aux: float | int | ArrayLike,
    temperature_source: float | int | ArrayLike,
    temperature_difference_aux: float | int | ArrayLike,
    temperature_difference_source: float | int | ArrayLike,
):
    """
    Calculate the fluid mixture fraction of the temperature difference source.

    Parameters
    ----------
    temperature_difference_source
    temperature_difference_aux
    temperature_aux
    temperature_source
    temperature_supply

    Returns
    -------

    Examples
    --------
    >>> a=5
    >>> top_frac = calculate_fluid_mixture(
    ...     temperature_difference_source=[20, 40, 60],
    ...     temperature_difference_aux=[60, 60, 60],
    ...     temperature_source=[60, 80, 100],
    ...     temperature_supply=[80, 80, 80],
    ...     temperature_aux=[100, 100, 101],
    ... )
    >>> [round(abs(float(t)), 3) for t in top_frac]
    [0.75, 0.0, 0.0]

    """
    temperature_supply = np.array(temperature_supply)
    temperature_source = np.array(temperature_source)
    temperature_aux = np.array(temperature_aux)
    temperature_difference_source = np.array(temperature_difference_source)
    temperature_difference_supply = np.array(temperature_difference_aux)
    # ToDo: Check equation!
    if any((temperature_source - temperature_aux)>=0):
        msg = "The auxiliary temperature must be above the source temperature."
        raise ValueError(msg)
    top_up_fraction = (
        (temperature_source - temperature_supply)
        * temperature_difference_supply
    ) / (
        (
            (temperature_supply - temperature_aux)
            * temperature_difference_source
        )
        + (
            (temperature_source - temperature_supply)
            * temperature_difference_supply
        )
    )
    top_up_fraction[top_up_fraction < 0] = 0
    return top_up_fraction
