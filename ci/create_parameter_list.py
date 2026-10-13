import ast
import csv
from pathlib import Path


def extract_parameters(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[dict]:
    """
    Extract function/method parameters with types and
    defaults.
    """
    params = []
    for arg in node.args.args:
        type_annotation = (
            ast.unparse(arg.annotation)
            if arg.annotation
            else "Any"
        )
        params.append(
            {
                "name": arg.arg,
                "type": type_annotation,
                "default": None,
            }
        )

    # Assign default values to parameters
    defaults = node.args.defaults
    defaults_offset = len(params) - len(defaults)

    for i, default in enumerate(defaults):
        idx = defaults_offset + i
        params[idx]["default"] = ast.unparse(default)

    return params


def extract_from_function(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[dict]:
    """
    Extract parameters from a top-level function.
    """
    records = []
    params = extract_parameters(func_node)

    for param in params:
        records.append(
            {
                "name": func_node.name,
                "callable_type": "Function",
                "parameter_name": param["name"],
                "type": param["type"],
                "default": param["default"] or "Mandatory",
            }
        )
    return records


def extract_from_class(
    class_node: ast.ClassDef,
) -> list[dict]:
    """
    Extract __init__ parameters from a class definition.
    """
    records = []
    for node in class_node.body:
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            if node.name == "__init__":
                params = extract_parameters(node)
                for param in params:
                    if param["name"] != "self":
                        records.append(
                            {
                                "name": class_node.name,
                                "callable_type": "Class",
                                "parameter_name": param["name"],
                                "type": param["type"],
                                "default": (
                                    param["default"]
                                    or "Mandatory"
                                ),
                            }
                        )
    return records


def extract_from_file(
    filepath: Path,
) -> list[dict]:
    """
    Parse a Python file and extract functions and
    classes.
    """
    records = []
    try:
        with open(
            filepath, encoding="utf-8"
        ) as file:
            content = file.read()
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return records

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            records.extend(extract_from_class(node))
        elif isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            records.extend(extract_from_function(node))

    return records


def scan_project(base_directory: str) -> list[dict]:
    """
    Recursively scan project directory for Python files.
    """
    base_path = Path(base_directory)
    records = []

    for py_file in base_path.rglob("*.py"):
        records.extend(extract_from_file(py_file))

    return records


def main(base_dir, output_file) -> None:
    """
    Execute the analysis and generate CSV report.
    """
    records = scan_project(base_dir)

    if not records:
        msg = (
            "No functions or classes found in "
            "the project."
        )
        print(msg)
        return

    with open(
        output_file, "w", newline="", encoding="utf-8"
    ) as csvfile:
        fieldnames = [
            "name",
            "callable_type",
            "parameter_name",
            "type",
            "default",
        ]
        writer = csv.DictWriter(
            csvfile, fieldnames=fieldnames
        )
        writer.writeheader()
        writer.writerows(records)

    print(f"Successfully created: {output_file}")
    print(f"Total parameters found: {len(records)}")


if __name__ == "__main__":
    main(
        Path(Path(__file__).parent.parent, "src"),
        "report.csv",
    )
