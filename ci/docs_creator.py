#!/usr/bin/env python3
"""
ci/docs_creator.py
===================
Introspects the installed oemof.eesyplan package and (re-)generates
the Sphinx API reference under docs/reference/.

Design decisions:
    * No icons/emojis.
    * No grid cards - replaced by genuine help text per category/module.
    * Each module is rendered ONCE as a dropdown (collapsed by
      default) - the file name only ever appears in the dropdown
      label.
    * Description text: module docstring -> first sentence of the
      docstring of the first public member -> omitted entirely if
      nothing is found (no plain listing of members any more).
    * The autosummary table is only shown if a module has MORE THAN
      ONE public member - with exactly one member it would merely
      repeat the name shown directly above the dropdown.
    * Dropdown label: instead of the raw file name, a readable,
      descriptive name is used. Order of precedence:
          1. Entry in the relevant label table
             (CORE_LABELS / COMPONENT_LABELS / GROUP_LABELS)
          2. Automatically derived from the (single) class name
             (_prettify), e.g. "PvPlant" -> "Pv Plant"
          3. Automatically derived from the file name if several
             members exist, e.g. "create_timeseries" ->
             "Create Timeseries"
      There are deliberately THREE separate label tables (rather than
      one global table), since e.g. "heat_demand" exists both as
      components/demand/heat_demand.py and as
      importer/heat_demand.py - a single global table would cause
      incorrect assignments here.

All components live on a SINGLE page (components.rst), organised into
sections. With furo and a corresponding sidebar configuration, the
sidebar displays these sections automatically.

No hard-coded class/file names are used for structure discovery itself
- this is determined at runtime via introspection. The label tables
below are purely optional labelling overrides.

Usage:
    tox -e docs
or manually in the matching venv:
    python ci/docs_creator.py
or automatically on every Sphinx build (see conf.py: setup() hook).
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import re
import shutil
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs" / "reference"
PACKAGE_ROOT = "oemof.eesyplan"

# ---------------------------------------------------------------------
# Manually curated help text (description shown under the
# module/category heading, BEFORE the dropdown).
# ---------------------------------------------------------------------

CORE_DESCRIPTIONS = {
    "gui": "Interactive model selection via tkinter.",
    "investment": (
        "Calculation of the capital recovery factor (CRF) and "
        "annuities for investment decisions."
    ),
    "io": "Helper functions for unpacking datapackages.",
    "model": (
        "Central energy system class, including optimisation and "
        "the results object."
    ),
    "project": (
        "Economic framework of a project (interest rate, lifetime, "
        "investment logic)."
    ),
    "type_checks": "Validation of input parameters.",
    "typemap": (
        "Mapping of datapackage identifiers to the corresponding "
        "component classes."
    ),
}

CATEGORY_DESCRIPTIONS = {
    "buses": (
        "Buses connect components within a single energy carrier "
        "(e.g. electricity, heat, gas)."
    ),
    "compansation": (
        "Balancing elements for energy excess and energy shortage."
    ),
    "converters": (
        "Converters between energy carriers, e.g. boilers, heat "
        "pumps, electrolysers and CHP units."
    ),
    "demand": (
        "Demand-side components for electricity, heat, fuel and "
        "hydrogen requirements."
    ),
    "production": (
        "Generation components such as PV, wind, biogas and geothermal plants."
    ),
    "providers": (
        "Connection to upstream supply networks (DSO) for "
        "electricity, gas, heat and hydrogen."
    ),
    "storages": (
        "Storage components for electrical, thermal, fuel and hydrogen energy."
    ),
    "transport": "Transport components such as heating networks and pipes.",
    "virtual": "Virtual components (currently unused).",
}

GROUP_DESCRIPTIONS = {
    "cop": (
        "Calculation of the coefficient of performance (COP) of "
        "heat pumps - either simplified or via TESPy."
    ),
    "heat_demand": (
        "Creation of heat load profiles based on BDEW standard load profiles."
    ),
    "create_timeseries": "Generation of time series for load profiles.",
    "create_timeseries_pv": (
        "Generation of PV feed-in time series (currently inactive, "
        "based on pvlib)."
    ),
    "weather_data": (
        "Reading and processing of DWD test reference year weather data."
    ),
    "energy_system": (
        "Building, solving and visualising an energy system from a "
        "datapackage."
    ),
    "results": "Export and import of optimisation results.",
    "balance": "Calculation of input/output balances of the components.",
    "graphs": "Creation of Sankey diagrams and capacity graphs.",
}

# ---------------------------------------------------------------------
# Labelling overrides for the dropdown headings (see dropdown_label()
# below for the full fallback chain). Keys are always the SHORT file
# name (without .py), NOT the full module path.
# ---------------------------------------------------------------------

CORE_LABELS: dict[str, str] = {
    "gui": "Interactive Model Selection (GUI)",
    "investment": "Investment Appraisal (CRF & Annuity)",
    "io": "Datapackage Extraction",
    "model": "Energy System & Optimisation",
    "project": "Project Framework",
    "type_checks": "Parameter Validation",
    "typemap": "Type Mapping (TYPEMAP)",
}

# Nested per category so that, for example, "heat_demand" (in
# components/demand/) cannot collide with "heat_demand" (in
# importer/).
COMPONENT_LABELS: dict[str, dict[str, str]] = {
    "buses": {
        "carrier": "Carrier Bus",
    },
    "compansation": {
        # TODO: file names in compansation/ not confirmed - classes
        # according to the project overview: Excess, Shortage.
        "excess": "Excess (Energy Surplus)",
        "shortage": "Shortage (Energy Deficit)",
    },
    "converters": {
        "auxiliary_heat": "Auxiliary Heat",
        "boiler": "Boiler",
        # TODO: confirm the actual class names in these two files
        # (presumably CHPFixedRatio / CHPVariableRatio or similar).
        "chp_fixed_ratio": "CHP (Fixed Ratio)",
        "chp_variable_ratio": "CHP (Variable Ratio)",
        "diesel_generator": "Diesel Generator",
        # TODO: confirm the actual class name.
        "electrical_transformator": "Electrical Transformer",
        "electrolyzer": "Electrolyser",
        "fuel_cell": "Fuel Cell",
        "heat_pump": "Heat Pump",
    },
    "demand": {
        "demand": "Demand (Base Class)",
        "electricity_demand": "Electricity Demand",
        "fuel_demand": "Fuel Demand",
        "heat_demand": "Heat Demand",
        "hydrogen_demand": "Hydrogen Demand",
        "sink": "Sink",
    },
    "production": {
        "biogas_plant": "Biogas Plant",
        "commodity": "Commodity",
        "geothermal_plant": "Geothermal Plant",
        "pv_plant": "PV Plant",
        "solar_thermal_plant": "Solar Thermal Plant",
        "source": "Source (Base Class)",
        "wind_turbine": "Wind Turbine",
    },
    "providers": {
        "dso": "DSO (Base Class)",
        "dso_electricity": "DSO Electricity",
        "dso_fuel": "DSO Fuel",
        "dso_heat": "DSO Heat",
        "dso_hydrogen": "DSO Hydrogen",
    },
    "storages": {
        # TODO: file names in storages/ not confirmed.
        "storage": "Energy Storage (Base Class)",
        "electrical_storage": "Electrical Storage",
        "fuel_storage": "Fuel Storage",
        "hydrogen_storage": "Hydrogen Storage",
        "thermal_storage": "Thermal Storage",
    },
    "transport": {
        # Confirmed (see the autodoc duplicate-object warning): a
        # single file "heat.py" contains both HeatingNetwork and
        # HeatingPipe.
        "heat": "Heating Network & Pipe",
    },
    "virtual": {},
}

GROUP_LABELS: dict[str, str] = {
    "cop": "COP Calculation",
    "heat_demand": "Heat Load Profiles (BDEW)",
    "create_timeseries": "Time Series Generation",
    "create_timeseries_pv": "PV Time Series (pvlib)",
    "weather_data": "Weather Data (DWD TRY)",
    "energy_system": "Energy System \u2194 Datapackage",
    "results": "Results Export/Import",
    "balance": "Input/Output Balances",
    "graphs": "Sankey & Capacity Diagrams",
}


# -----------------------------------------------------------------------
# Introspection helpers
# -----------------------------------------------------------------------


def safe_import(name: str):
    try:
        return importlib.import_module(name)
    except Exception as exc:
        print(f"⚠️  Skipping '{name}': {exc}")
        return None


def public_members(mod) -> list[str]:
    out = []
    for name, obj in inspect.getmembers(mod):
        if name.startswith("_"):
            continue
        if inspect.isclass(obj) or inspect.isfunction(obj):
            if getattr(obj, "__module__", None) == mod.__name__:
                out.append(name)
    return sorted(out)


def _first_sentence(doc: str) -> str:
    """Collapse the first paragraph of a docstring into a single line."""
    paragraph: list[str] = []
    for line in doc.splitlines():
        stripped = line.strip()
        if not stripped and paragraph:
            break
        if stripped:
            paragraph.append(stripped)
    return " ".join(paragraph)


def module_description(mod, overrides: dict[str, str]) -> str:
    """Determine the description text.

    Order of precedence:
        1. Manual override (CORE_DESCRIPTIONS, etc.)
        2. First paragraph of the module docstring
        3. First paragraph of the docstring of the first public
           member (e.g. the class, if the module itself has no
           docstring of its own)
        4. Empty string - the description is then omitted entirely,
           rather than showing a plain listing of members.
    """
    short = mod.__name__.rsplit(".", 1)[-1]
    if short in overrides:
        return overrides[short]

    doc = (mod.__doc__ or "").strip()
    if doc:
        sentence = _first_sentence(doc)
        if sentence:
            return sentence

    for member_name in public_members(mod):
        member_doc = (getattr(mod, member_name).__doc__ or "").strip()
        if member_doc:
            sentence = _first_sentence(member_doc)
            if sentence:
                return sentence

    return ""


def _prettify(name: str) -> str:
    """Convert CamelCase ("PvPlant") or snake_case
    ("create_timeseries_pv") into a readable, space-separated form
    ("Pv Plant" / "Create Timeseries Pv"). Fully capitalised acronyms
    (e.g. "DSO", "CHP") are preserved as-is.

    Note: compound acronym words such as "DsoElectricity" are NOT
    recognised as "DSO Electricity" (to the regex, "Dso" simply looks
    like an ordinary word) - for such cases, please add an entry to
    the relevant label table instead.
    """
    if "_" in name:
        words = [p for p in name.split("_") if p]
    else:
        words = re.findall(
            r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", name
        )
        if not words:
            words = [name]

    return " ".join(w if w.isupper() else w[:1].upper() + w[1:] for w in words)


def dropdown_label(
    full_name: str, members: list[str], labels: dict[str, str]
) -> str:
    """Determine the heading used for the dropdown.

    Order of precedence:
        1. Entry in the given label table (keyed by file name)
        2. Name of the single public member, prettified
           (e.g. class "PvPlant" -> "Pv Plant")
        3. File name, prettified (fallback for several members
           without a table entry, e.g. "graphs")
    """
    short = full_name.rsplit(".", 1)[-1]
    if short in labels:
        return labels[short]
    if len(members) == 1:
        return _prettify(members[0])
    return _prettify(short)


def discover_subpackages(
    package_name: str,
) -> dict[str, list[tuple[str, object]]]:
    """subpackage_short_name -> [(full_dotted_module_name, module), ...]"""
    package = safe_import(package_name)
    if package is None or not hasattr(package, "__path__"):
        return {}

    result: dict[str, list[tuple[str, object]]] = {}
    seen_pkgs: set[str] = set()
    for _, name, ispkg in pkgutil.iter_modules(
        package.__path__, package_name + "."
    ):
        if not ispkg or name in seen_pkgs:
            continue
        seen_pkgs.add(name)
        short = name.rsplit(".", 1)[-1]
        sub_pkg = safe_import(name)
        submodules: list[tuple[str, object]] = []
        seen_mods: set[str] = set()
        if sub_pkg is not None and hasattr(sub_pkg, "__path__"):
            for _, subname, sub_ispkg in pkgutil.iter_modules(
                sub_pkg.__path__, name + "."
            ):
                if sub_ispkg or subname in seen_mods:
                    continue
                seen_mods.add(subname)
                mod = safe_import(subname)
                if mod is not None:
                    submodules.append((subname, mod))
        result[short] = submodules
    return result


def discover_flat_modules(*names: str) -> list[tuple[str, object]]:
    out: list[tuple[str, object]] = []
    seen: set[str] = set()
    for name in names:
        obj = safe_import(name)
        if obj is None:
            continue
        if hasattr(obj, "__path__"):
            for _, subname, ispkg in pkgutil.iter_modules(
                obj.__path__, name + "."
            ):
                if ispkg or subname in seen:
                    continue
                seen.add(subname)
                mod = safe_import(subname)
                if mod is not None:
                    out.append((subname, mod))
        elif name not in seen:
            seen.add(name)
            out.append((name, obj))
    return out


def discover_root_modules(package_name: str) -> list[tuple[str, object]]:
    """Modules directly in the package root (not inside subpackages)."""
    package = safe_import(package_name)
    if package is None:
        return []
    out = []
    seen: set[str] = set()
    for _, name, ispkg in pkgutil.iter_modules(
        package.__path__, package_name + "."
    ):
        if ispkg or name in seen:
            continue
        seen.add(name)
        mod = safe_import(name)
        if mod is not None:
            out.append((name, mod))
    return out


# -----------------------------------------------------------------------
# RST building blocks
# -----------------------------------------------------------------------


def rst_title(text: str, char: str = "=") -> str:
    return f"{text}\n{char * len(text)}\n"


def autosummary_block(full_names_members: list[tuple[str, str]]) -> str:
    if not full_names_members:
        return ""
    lines = ".. autosummary::\n    :nosignatures:\n\n"
    for full_name, member in full_names_members:
        lines += f"    ~{full_name}.{member}\n"
    return lines + "\n"


def dropdown_block(module_path: str, label: str) -> str:
    """The dropdown is collapsed by default (no ':open:' option).

    The __init__ docstring is already merged into the class
    description via conf.py's 'autoclass_content = "both"'. A
    dedicated "autodoc-skip-member" hook in conf.py additionally
    prevents __init__ from being rendered as its own object, which
    would otherwise cause both a duplicated description and an extra
    nesting level in Furo's "On this page" navigation.
    """
    return (
        f".. dropdown:: {label}\n\n"
        f"    .. automodule:: {module_path}\n"
        f"        :members:\n"
        f"        :undoc-members:\n"
        f"        :show-inheritance:\n\n"
    )


def module_block(
    full_name: str,
    mod,
    descriptions: dict[str, str],
    labels: dict[str, str],
) -> str:
    """Description + (optional) autosummary + a single dropdown.

    The file name itself no longer appears anywhere - instead, a
    readable, descriptive name is used as the dropdown label (see
    dropdown_label()). The autosummary table is only shown if there is
    more than one public member.
    """
    content = ""

    description = module_description(mod, descriptions)
    if description:
        content += description + "\n\n"

    members = public_members(mod)
    if len(members) > 1:
        content += autosummary_block([(full_name, m) for m in members])

    label = dropdown_label(full_name, members, labels)
    content += dropdown_block(full_name, label)
    return content


# -----------------------------------------------------------------------
# Page builders
# -----------------------------------------------------------------------


def build_main_index() -> str:
    sections = [
        (
            "core",
            "Core infrastructure: energy system, project data, "
            "investment logic, input/output and the GUI.",
        ),
        (
            "components",
            "All solph-related building blocks: buses, converters, "
            "demand, production, providers, storages and transport.",
        ),
        (
            "importer",
            "Preparation of input data: COP calculation, load "
            "profiles, weather data.",
        ),
        (
            "datapackage",
            "Building, as well as exporting/importing, energy "
            "systems via datapackages.",
        ),
        (
            "postprocessing",
            "Post-processing of optimisation results: balances and diagrams.",
        ),
    ]

    content = ".. _eesyplan-reference-label:\n\n"
    content += rst_title("API Reference") + "\n"
    content += (
        "This reference describes the public Python API of "
        "``oemof.eesyplan``.\n\n"
    )
    for doc, desc in sections:
        content += f":doc:`{doc}`\n    {desc}\n\n"

    content += (
        ".. toctree::\n    :maxdepth: 2\n    :hidden:\n\n"
        "    core\n    components\n    importer\n    datapackage\n"
        "    postprocessing\n"
    )
    return content


def build_flat_group_page(
    title: str,
    modules: list[tuple[str, object]],
    descriptions: dict[str, str],
    labels: dict[str, str],
) -> str:
    content = rst_title(title) + "\n"
    if not modules:
        return content + "No modules were found.\n"

    for full_name, mod in modules:
        content += module_block(full_name, mod, descriptions, labels)
        content += "\n"
    return content


def build_components_page(
    categories: dict[str, list[tuple[str, object]]],
) -> str:
    content = rst_title("Components") + "\n"
    content += (
        "This page describes all solph-related building blocks, "
        "organised by category.\n\n"
    )

    for key, submodules in categories.items():
        title = key.replace("_", " ").title()
        content += rst_title(title, "-") + "\n"
        content += (
            CATEGORY_DESCRIPTIONS.get(key, "No description available.")
            + "\n\n"
        )

        if not submodules:
            content += "This module is currently empty.\n\n"
            continue

        labels = COMPONENT_LABELS.get(key, {})

        any_rendered = False
        for subname, mod in submodules:
            if not public_members(mod):
                continue
            any_rendered = True
            content += module_block(subname, mod, {}, labels)
            content += "\n"

        if not any_rendered:
            content += "No public members were found.\n\n"

    return content


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"✅ written: {path}")


def clean_previous_output() -> None:
    """Remove every file managed by this script - no stale output."""
    for name in (
        "index.rst",
        "core.rst",
        "components.rst",
        "importer.rst",
        "datapackage.rst",
        "postprocessing.rst",
    ):
        f = DOCS_DIR / name
        if f.exists():
            f.unlink()
            print(f"🧹 removed: {f}")
    # Legacy structure from an earlier revision (components/ as a
    # directory):
    components_dir = DOCS_DIR / "components"
    if components_dir.exists():
        shutil.rmtree(components_dir)
        print(f"🧹 removed (legacy): {components_dir}")


def main() -> None:
    clean_previous_output()

    categories = discover_subpackages(f"{PACKAGE_ROOT}.components")
    core_modules = discover_root_modules(PACKAGE_ROOT)
    importer_modules = discover_flat_modules(
        f"{PACKAGE_ROOT}.importer", f"{PACKAGE_ROOT}.weather"
    )
    datapackage_modules = discover_flat_modules(f"{PACKAGE_ROOT}.datapackage")
    postprocessing_modules = discover_flat_modules(
        f"{PACKAGE_ROOT}.postprocessing"
    )

    structure: dict[Path, str] = {
        DOCS_DIR / "index.rst": build_main_index(),
        DOCS_DIR / "core.rst": build_flat_group_page(
            "Core / Framework", core_modules, CORE_DESCRIPTIONS, CORE_LABELS
        ),
        DOCS_DIR / "components.rst": build_components_page(categories),
        DOCS_DIR / "importer.rst": build_flat_group_page(
            "Importer", importer_modules, GROUP_DESCRIPTIONS, GROUP_LABELS
        ),
        DOCS_DIR / "datapackage.rst": build_flat_group_page(
            "Datapackage I/O",
            datapackage_modules,
            GROUP_DESCRIPTIONS,
            GROUP_LABELS,
        ),
        DOCS_DIR / "postprocessing.rst": build_flat_group_page(
            "Postprocessing",
            postprocessing_modules,
            GROUP_DESCRIPTIONS,
            GROUP_LABELS,
        ),
    }

    for path, content in structure.items():
        write_file(path, content)

    print(f"\n🎉 Done! {len(structure)} files under: {DOCS_DIR}")


if __name__ == "__main__":
    main()
