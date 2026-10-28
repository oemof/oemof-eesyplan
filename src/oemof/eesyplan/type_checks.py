from numbers import Number

import numpy as np
from numpy.typing import ArrayLike


def check_parameter(*args):
    for a in args:
        if a is None:
            raise ValueError("None is not allowed.")


def to_array_or_number(x: Number | ArrayLike):
    """
    Gibt x unverändert zurück, falls es eine Zahl (int/float) ist.
    Andernfalls wird x in ein NumPy-Array umgewandelt.
    """
    if isinstance(x, (Number, type(None))):
        return x
    return np.asarray(x)
