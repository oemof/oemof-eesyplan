from typing import Any
from typing import TypeAlias
from typing import overload

import numpy as np
import numpy.typing as npt

ArrayLikeInput: TypeAlias = npt.ArrayLike  # no pd.Series, so no Any
ScalarInput: TypeAlias = int | float | np.integer[Any] | np.floating[Any]
ArrayOutput: TypeAlias = npt.NDArray[np.float64]


@overload
def normalise(value: None) -> None: ...


@overload
def normalise(value: ScalarInput) -> float: ...  # type: ignore[overload-overlap]


@overload
def normalise(value: ArrayLikeInput) -> ArrayOutput: ...


def normalise(
    value: ArrayLikeInput | ScalarInput | None,
) -> ArrayOutput | float | None:
    """Convert a value to ``float64`` while preserving its shape.

    ``None`` is passed through unchanged. Scalars (and zero-dimensional
    inputs) are returned as a built-in ``float``. Array-like inputs, such
    as lists, tuples, arrays and Series, are returned as a ``float64``
    NumPy array of the same shape.

    Args:
        value: |value|

    Returns:
        ``None`` if ``value`` is ``None``; a ``float`` if ``value`` is a
        scalar; otherwise a ``float64`` array of the same shape.

    Raises:
        ValueError: If the value cannot be converted, for example a
            non-numeric string.
        TypeError: If the type of the value is not supported, for example
            a dictionary.

    Note:
        A zero-dimensional array such as ``np.array(5.0)`` is returned as
        a ``float`` at runtime, although the type hints declare an array.

    Examples:
        >>> normalise(None) is None
        True
        >>> normalise("1.5")
        1.5
        >>> normalise([1, 2])
        array([1., 2.])
    """
    if value is None:
        return None

    arr = np.asarray(value, dtype=np.float64)
    return float(arr) if arr.ndim == 0 else arr
