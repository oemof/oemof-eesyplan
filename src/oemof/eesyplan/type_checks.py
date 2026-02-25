def check_parameter(*args):
    for a in args:
        if a is None:
            raise ValueError("None is not allowed.")
