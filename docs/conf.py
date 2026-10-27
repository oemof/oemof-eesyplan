"""Sphinx configuration for the ``oemof-eesyplan`` documentation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sphinx.application import Sphinx


# -- Paths -------------------------------------------------------------------

DOCS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = DOCS_ROOT.parent  # kept for optional sys.path tweaks

#: Snippet injected into every page so that shared parameter descriptions
#: can be reused as substitutions.
PARAMETER_DESCRIPTIONS = (
    DOCS_ROOT / "reference" / "docstring_parameter_description.rst"
)

#: Members that must never be documented as standalone entries.
SKIPPED_MEMBERS = frozenset({"__init__", "__len__"})


# -- Extension hooks ---------------------------------------------------------


def _skip_dunder_members(
    app: Sphinx,
    what: str,
    name: str,
    obj: object,
    skip: bool,
    options: Any,
) -> bool:
    """Suppress selected dunder members as standalone objects.

    Rendering ``__init__`` separately creates a nested entry in Furo's
    "On this page" navigation. The docstring content is not lost: because
    ``autoclass_content = "both"`` it is already merged into the class
    description by an independent mechanism.
    """
    if name in SKIPPED_MEMBERS:
        return True
    return skip


def setup(app: Sphinx) -> dict[str, Any]:
    """Register local Sphinx event handlers."""
    app.connect("autodoc-skip-member", _skip_dunder_members, priority=100)
    return {
        "version": "0.0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }


# -- Project information -----------------------------------------------------

project = "oemof-eesyplan"
year = "2025-2026"
author = "Open Plan Community"
copyright = f"{year}, {author}"
version = release = "0.0.1"
language = "en"


# -- General configuration ---------------------------------------------------

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

source_suffix = ".rst"
master_doc = "index"
templates_path = ["."]
pygments_style = "trac"

# The parameter description file is only a snippet, so it must not be built
# as a page of its own.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    PARAMETER_DESCRIPTIONS.relative_to(DOCS_ROOT).as_posix(),
]

# Shared substitutions appended to every source file.
rst_epilog = PARAMETER_DESCRIPTIONS.read_text(encoding="utf-8")


# -- autodoc / autosummary ---------------------------------------------------

autosummary_generate = True

# Show the class docstring *and* the ``__init__`` docstring together.
autoclass_content = "both"
napoleon_include_init_with_doc = False


# -- Napoleon ----------------------------------------------------------------

napoleon_use_ivar = True
napoleon_use_rtype = False
napoleon_use_param = False


# -- External links ----------------------------------------------------------

_REPO_URL = "https://github.com/oemof/oemof-eesyplan"

extlinks = {
    "issue": (f"{_REPO_URL}/issues/%s", "#%s"),
    "pr": (f"{_REPO_URL}/pull/%s", "PR #%s"),
    "code": (f"{_REPO_URL}/blob/main/src/oemof/eesyplan/%s", "%s"),
}

linkcheck_ignore = [
    r"https://coveralls\.io",
]


# -- HTML output (Furo theme) ------------------------------------------------

html_theme = "furo"

html_theme_options = {
    "sidebar_hide_name": True,  # the logo already carries the project name
    "navigation_with_keys": True,
    "light_logo": "dummy_light.svg",
    "dark_logo": "dummy_dark.svg",
}

html_static_path = ["_static"]
html_short_title = f"{project}-{version}"
html_last_updated_fmt = "%b %d, %Y"
html_use_smartypants = True
html_split_index = False
