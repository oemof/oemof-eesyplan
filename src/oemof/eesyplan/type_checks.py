from typing import Any
from typing import SupportsFloat

import numpy as np
from numpy.typing import ArrayLike
from numpy.typing import NDArray

from oemof.eesyplan.project import Project
from oemof.network import Node


def check_parameter(*args):
    for a in args:
        if a is None:
            raise ValueError("None is not allowed.")


def ct(
    x: SupportsFloat | ArrayLike | str | Project | Node | None,
) -> NDArray[Any] | float | str | Node | None | Project:
    """
    Clean Type.

    Within eesyplan only some types are allowed but it is okay if non-allowed
    values can be converted to allowed values. Furthermore, some read functions
    will read None (NoneType) as "None" (string) which leads to errors.
    """
    if isinstance(x, str):
        if x == "None":
            return None
        return x
    elif isinstance(x, SupportsFloat):
        return float(x)
    elif x is None or isinstance(x, (Node, Project)):
        return x
    return np.asarray(x)
