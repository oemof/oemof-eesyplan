import sys
from pathlib import Path

DOCS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = DOCS_ROOT.parent

# "ci" liegt im Projekt-Root, nicht relativ zu docs/ - daher für den
# Import erreichbar machen.
sys.path.insert(0, str(PROJECT_ROOT))


def _skip_dunder_members(app, what, name, obj, skip, options):
    """__init__ (und ggf. weitere Dunder) nie als eigenständiges Objekt
    rendern - verhindert den verschachtelten Eintrag in Furos
    "On this page"-Navigation. Der Inhalt des __init__-Docstrings bleibt
    trotzdem erhalten, da autoclass_content = "both" ihn bereits in die
    Klassenbeschreibung selbst integriert (unabhängiger Mechanismus).
    """
    if name in {"__init__", "__len__"}:
        return True
    return skip


def setup(app):
    app.connect("autodoc-skip-member", _skip_dunder_members, priority=100)


# -- Parameter-Substitutionen (rst_epilog) ----------------------------------

exclude_patterns = [
    "reference/docstring_parameter_description.rst",
]

with Path(
    DOCS_ROOT / "reference" / "docstring_parameter_description.rst"
).open(
    encoding="utf-8",
) as _f:
    rst_epilog = _f.read()


# -- Allgemeine Konfiguration ------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.extlinks",
    "sphinx.ext.ifconfig",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx_design",
]

autosummary_generate = True

# Zeigt Klassen-Docstring UND __init__-Docstring zusammen an.
autoclass_content = "both"
napoleon_include_init_with_doc = False

source_suffix = ".rst"
master_doc = "index"

project = "oemof-eesyplan"
year = "2025-2026"
author = "Open Plan Community"
copyright = f"{year}, {author}"
version = release = "0.0.1"

pygments_style = "trac"
templates_path = ["."]

extlinks = {
    "issue": ("https://github.com/oemof/oemof-eesyplan/issues/%s", "#%s"),
    "pr": ("https://github.com/oemof/oemof-eesyplan/pull/%s", "PR #%s"),
    "code": (
        "https://github.com/oemof/oemof-eesyplan/blob/main/"
        "src/oemof/eesyplan/%s",
        "%s",
    ),
}

napoleon_use_ivar = True
napoleon_use_rtype = False
napoleon_use_param = False

linkcheck_ignore = [
    "https://coveralls.io",
]


# -- HTML-Ausgabe (Furo-Theme) -----------------------------------------------

html_theme = "furo"

html_theme_options = {
    "sidebar_hide_name": True,  # Logo zeigt den Namen schon
    "navigation_with_keys": True,
    "light_logo": "dummy_light.svg",
    "dark_logo": "dummy_dark.svg",
}

html_use_smartypants = True
html_last_updated_fmt = "%b %d, %Y"
html_split_index = False
html_short_title = f"{project}-{version}"
html_static_path = ["_static"]
