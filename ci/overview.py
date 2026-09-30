"""
Generiert eine CSV-Uebersicht aller Klassen im components-Ordner von eesyplan.

Pro Parameter einer Klasse werden folgende Informationen erfasst:
  - Parameter-Name
  - Typ
  - Typ_Quelle  : docstring | konstruktor (Default) | annotation | geraten
  - Erklaerung   : aufgeloester Erklartext
  - Erklaerung_Quelle : docstring | rst:|verweis| | Mischung aus beidem
                       (Segmente getrennt durch " | ")

Das Skript liest die Docstrings (aus dem __init__!) + Konstruktor-Signaturen
und die RST-Datei docstring_parameter_description.rst.
"""

from __future__ import annotations

import csv
import importlib.util
import inspect
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPONENTS_DIR = PROJECT_ROOT / "src" / "oemof" / "eesyplan" / "components"
RST_FILE = PROJECT_ROOT / "docs" / "reference" / "docstring_parameter_description.rst"
OUTPUT = PROJECT_ROOT / "ci" / "component_parameters.csv"


# ---------------------------------------------------------------------------
# 1. RST-Replacements einlesen:  |name| -> Beschreibungstext
# ---------------------------------------------------------------------------
def load_rst_descriptions(rst_path: Path) -> dict[str, str]:
    """Extrahiert aus der RST-Datei die Substitutionen |key| replace:: text."""
    if not rst_path.exists():
        return {}
    text = rst_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\.\. \|(?P<key>[^|]+)\| replace::\s*(?P<text>.*?)(?=\n\n\.\. \||\n\Z)",
        re.DOTALL,
    )
    result = {}
    for match in pattern.finditer(text):
        # Mehrzeiligen Text zusammenfuegen
        desc = " ".join(match.group("text").split())
        result[match.group("key")] = desc
    return result


# ---------------------------------------------------------------------------
# 2. Klassen + Docstring-Parameter per AST / inspect sammeln
# ---------------------------------------------------------------------------
def iter_component_files():
    for py_file in sorted(COMPONENTS_DIR.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue
        yield py_file


def parse_docstring_params(docstring: str) -> dict[str, dict]:
    """Liest die 'Parameters'-Sektion eines numpydoc-Docstrings.

    Unterstuetzt das uebliche Format:  ``name : typ`` auf einer Zeile,
    Beschreibung/|referenz| in den eingerueckten Folgezeilen.

    Rueckgabe: { param_name: {"typ": str, "beschreibung": str} }
    """
    result: dict[str, dict] = {}
    if not docstring:
        return result

    # Versuche erst das numpydoc-Format
    m = re.search(
        r"^\s*Parameters\s*\n\s*[-=]+\s*\n"
        r"(?P<body>.*?)"
        r"(?=\n\s*(Examples|Returns|Raises|Notes|Yields|Warns|References|"
        r"See Also|Attributes|Methods)\s*\n|\Z)",
        docstring,
        re.DOTALL | re.MULTILINE,
        )

    # Wenn numpydoc-Format nicht gefunden, versuche einfacheres Format
    if not m:
        m = re.search(
            r"^\s*Parameters\s*\n"
            r"(?P<body>.*?)"
            r"(?=\n\s*(Examples|Returns|Raises|Notes|Yields|Warns|References|"
            r"See Also|Attributes|Methods)\s*\n|\Z)",
            docstring,
            re.DOTALL | re.MULTILINE,
            )

    if not m:
        return result

    body = m.group("body")
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # Parameter-Zeile: "name : typ"  (kein |referenz|, nicht leer)
        pm = re.match(r"^\s*(\w+)\s*:\s*(.*?)\s*$", line)
        if pm and not line.lstrip().startswith("|"):
            name = pm.group(1)
            typ = pm.group(2).strip()
            desc_lines = []
            i += 1
            # Folgezeilen (eingerueckte, nicht leer) = Beschreibung
            while i < len(lines):
                next_line = lines[i]
                # Wenn leere Zeile oder nicht-eingerueckte Zeile -> STOP
                if not next_line.strip():
                    i += 1
                    break
                if not next_line.startswith("    ") and not next_line.startswith("\t"):
                    break
                desc_lines.append(next_line.strip())
                i += 1
            beschreibung = " ".join(desc_lines).strip()
            result[name] = {
                "typ": typ,
                "beschreibung": beschreibung,
            }
        else:
            i += 1

    return result


def resolve_description(text: str, rst_desc: dict[str, str]) -> tuple[str, str]:
    """Loest |sphinx-verweise| im Beschreibungstext auf.

    Der Text wird in Segmente zerlegt: reiner Docstring-Text bleibt erhalten,
    |verweise| werden durch den RST-Text ersetzt.

    Rueckgabe: (erklaerung, quelle). 'quelle' enthaelt ein Segment pro
    Texteil, getrennt durch " | ". Beispiele:
      - "docstring"                     (reiner Docstring-Text)
      - "rst:|name|"                    (reiner Sphinx-Verweis)
      - "docstring | rst:|bus_in| | docstring"  (gemischt)
    """
    parts: list[tuple[str, str]] = []
    pos = 0
    for match in re.finditer(r"\|\s*([^|]+?)\s*\|", text):
        literal = text[pos:match.start()].strip()
        if literal:
            parts.append((literal, "docstring"))
        key = match.group(1).strip()
        resolved = rst_desc.get(key, f"(fehlender RST-Text: {key})")
        parts.append((resolved, f"rst:|{key}|"))
        pos = match.end()
    if pos < len(text):
        literal = text[pos:].strip()
        if literal:
            parts.append((literal, "docstring"))

    if not parts:
        return "", ""
    erklaerung = " ".join(t for t, _ in parts)
    quelle = " | ".join(s for _, s in parts)
    return erklaerung, quelle


# ---------------------------------------------------------------------------
# 3. Hauptlogik
# ---------------------------------------------------------------------------
def build_rows(rst_desc: dict[str, str]) -> list[dict]:
    rows = []

    for py_file in iter_component_files():
        mod_name = str(py_file.relative_to(PROJECT_ROOT)).replace(
            "/", "."
        )[:-3]

        spec = importlib.util.spec_from_file_location(mod_name, py_file)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # Import-Fehler tolerieren
            print(f"  [WARN] {py_file.name} konnte nicht importiert werden: {exc}")
            continue

        for name, obj in vars(module).items():
            if not inspect.isclass(obj) or obj.__module__ != mod_name:
                continue

            # WICHTIG: Die Docstrings stehen im __init__ (nicht an der Klasse!).
            # inspect.getdoc(obj) wuerde fuer diese Klassen None liefern.
            docstring = inspect.getdoc(obj.__init__)
            if not docstring or "Parameters" not in docstring:
                docstring = inspect.getdoc(obj)
            doc_params = parse_docstring_params(docstring)

            try:
                sig = inspect.signature(obj.__init__)
            except (ValueError, TypeError):
                continue

            for param in sig.parameters.values():
                if param.name in ("self", "args", "kwargs"):
                    continue

                doc_entry = doc_params.get(param.name)

                # --- Typ-Ermittlung ---
                if doc_entry and doc_entry["typ"]:
                    typ = doc_entry["typ"].split(",")[0].strip()
                    typ_quelle = "docstring"
                elif param.default is not inspect.Parameter.empty:
                    typ = type(param.default).__name__
                    typ_quelle = "konstruktor"
                elif param.annotation is not inspect.Parameter.empty:
                    typ = str(param.annotation)
                    typ_quelle = "annotation"
                else:
                    typ = "(unbekannt)"
                    typ_quelle = "geraten"

                # --- Erklaerung-Ermittlung ---
                if doc_entry and doc_entry["beschreibung"].strip():
                    beschreibung = doc_entry["beschreibung"]
                    erklaerung, quelle = resolve_description(beschreibung, rst_desc)
                    if erklaerung:
                        erklaerung_quelle = quelle
                    else:
                        erklaerung = "(keine Beschreibung)"
                        erklaerung_quelle = "docstring"
                elif doc_entry and doc_entry["typ"]:
                    erklaerung = "(keine Beschreibung, nur Typ im Docstring)"
                    erklaerung_quelle = "docstring"
                else:
                    erklaerung = "(kein Eintrag im Docstring)"
                    erklaerung_quelle = "-"

                # --- Default ---
                if param.default is not inspect.Parameter.empty:
                    default = str(param.default)
                else:
                    default = "-"

                rows.append(
                    {
                        "Klasse": obj.__name__,
                        "Modul": py_file.parent.name + "/" + py_file.name,
                        "Parameter": param.name,
                        "Typ": str(typ),
                        "Typ_Quelle": typ_quelle,
                        "Erklaerung": erklaerung,
                        "Erklaerung_Quelle": erklaerung_quelle,
                        "Default": default,
                    }
                )

    return rows


def main():
    print("Lese RST-Datei ...")
    rst_desc = load_rst_descriptions(RST_FILE)
    print(f"  {len(rst_desc)} Replacements geladen.")

    print("Analysiere components-Module ...")
    rows = build_rows(rst_desc)
    print(f"  {len(rows)} Parameter gefunden.")

    if rows:
        fieldnames = list(rows[0].keys())
        with OUTPUT.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Fertig. CSV geschrieben nach: {OUTPUT}")
    else:
        print("Keine Parameter gefunden - CSV nicht erstellt.")


if __name__ == "__main__":
    main()
