import ast
import csv
import re
from pathlib import Path


def extract_parameters(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[dict[str, str]]:
    """
    Extract parameters, type annotations and default values.
    """
    parameters = []

    positional_arguments = [
        *node.args.posonlyargs,
        *node.args.args,
    ]

    defaults_offset = len(positional_arguments) - len(node.args.defaults)

    for index, argument in enumerate(positional_arguments):
        annotation = (
            ast.unparse(argument.annotation) if argument.annotation else "Any"
        )

        default = "Mandatory"
        default_index = index - defaults_offset

        if default_index >= 0:
            default = ast.unparse(node.args.defaults[default_index])

        if argument.arg not in {"self", "cls"}:
            parameters.append(
                {
                    "parameter_name": argument.arg,
                    "type": annotation,
                    "default": default,
                }
            )

    for argument, default_node in zip(
        node.args.kwonlyargs,
        node.args.kw_defaults,
        strict=False,
    ):
        annotation = (
            ast.unparse(argument.annotation) if argument.annotation else "Any"
        )

        default = (
            "Mandatory" if default_node is None else ast.unparse(default_node)
        )

        parameters.append(
            {
                "parameter_name": argument.arg,
                "type": annotation,
                "default": default,
            }
        )

    return parameters


def extract_from_function(
    function_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[dict[str, str]]:
    """
    Extract parameters from a top-level function.
    """
    records = []

    for parameter in extract_parameters(function_node):
        records.append(
            {
                "Parameter": parameter["parameter_name"],
                "Name": function_node.name,
                "Callable type": "Function",
                "Type": parameter["type"],
                "Default": parameter["default"],
            }
        )

    return records


def extract_from_class(
    class_node: ast.ClassDef,
) -> list[dict[str, str]]:
    """
    Extract parameters from a class constructor.
    """
    records = []

    for node in class_node.body:
        is_method = isinstance(
            node,
            (ast.FunctionDef | ast.AsyncFunctionDef),
        )

        if is_method and node.name == "__init__":
            for parameter in extract_parameters(node):
                records.append(
                    {
                        "Parameter": parameter["parameter_name"],
                        "Name": class_node.name,
                        "Callable type": "Class",
                        "Type": parameter["type"],
                        "Default": parameter["default"],
                    }
                )

    return records


def extract_from_file(filepath: Path) -> list[dict[str, str]]:
    """
    Parse one Python file and extract functions and classes.
    """
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []

    records = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            records.extend(extract_from_class(node))
        elif isinstance(
            node,
            (ast.FunctionDef | ast.AsyncFunctionDef),
        ):
            records.extend(extract_from_function(node))

    return records


def scan_project(base_directory: Path) -> list[dict[str, str]]:
    """
    Recursively scan a project for Python files.
    """
    records = []

    for filepath in base_directory.rglob("*.py"):
        records.extend(extract_from_file(filepath))

    return records


def parse_rst_parameters(
    filepath: Path,
) -> list[dict[str, str]]:
    """
    Parse parameter descriptions from an RST file.
    """
    parameter_records = []
    lines = filepath.read_text(encoding="utf-8").splitlines()

    index = 0

    while index < len(lines):
        match = re.match(
            r"^\.\.\s+\|([^|]+)\|\s+replace::\s*(.*)$",
            lines[index],
        )

        if not match:
            index += 1
            continue

        parameter_name = match.group(1).strip()
        text = match.group(2).strip()
        index += 1

        continuation = []

        while index < len(lines):
            line = lines[index]

            if line.strip() and not line.startswith((" ", "\t")):
                break

            if line.strip():
                continuation.append(line.strip())

            index += 1

        if continuation:
            text = " ".join([text, *continuation]).strip()

        parameter_records.append(
            {
                "Parameter": parameter_name,
                "Text": text,
            }
        )

    return parameter_records


def merge_records(
    code_records: list[dict[str, str]],
    description_records: list[dict[str, str]],
) -> list[dict[str, str]]:
    """
    Merge code parameters and descriptions by parameter name.
    """
    output_fields = [
        "Parameter",
        "Name",
        "Callable type",
        "Type",
        "Default",
        "Text",
    ]

    descriptions = {
        record["Parameter"]: record["Text"] for record in description_records
    }

    code_parameters = set()

    merged_records = []

    for record in code_records:
        parameter_name = record["Parameter"]
        code_parameters.add(parameter_name)

        merged_records.append(
            {field: record.get(field, "") for field in output_fields[:-1]}
            | {"Text": descriptions.get(parameter_name, "")}
        )

    for record in description_records:
        parameter_name = record["Parameter"]

        if parameter_name not in code_parameters:
            merged_records.append(
                {
                    "Parameter": parameter_name,
                    "Name": "",
                    "Callable type": "",
                    "Type": "",
                    "Default": "",
                    "Text": record["Text"],
                }
            )

    return merged_records


def write_csv(
    filepath: Path,
    records: list[dict[str, str]],
) -> None:
    """
    Write merged records to one CSV file.
    """
    fieldnames = [
        "Parameter",
        "Name",
        "Callable type",
        "Type",
        "Default",
        "Text",
    ]

    with filepath.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    """
    Create one merged CSV report.
    """
    script_directory = Path(__file__).resolve().parent
    project_directory = script_directory.parent / "src"
    rst_file = (
        script_directory.parent
        / "docs"
        / "reference"
        / "docstring_parameter_description.rst"
    )
    output_file = script_directory / "parameter_report.csv"

    code_records = scan_project(project_directory)
    description_records = parse_rst_parameters(rst_file)
    merged_records = merge_records(
        code_records,
        description_records,
    )

    write_csv(output_file, merged_records)

    print(f"Successfully created: {output_file}")
    print(f"Total records written: {len(merged_records)}")


if __name__ == "__main__":
    main()
