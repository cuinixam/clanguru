# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import os
import sys
from pathlib import Path

import mlx.traceability

project_root_path = Path(__file__).parent.parent

for path in ["src", "tests"]:
    sys.path.insert(0, project_root_path.joinpath(path).as_posix())


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "clanguru"
copyright = "2024, cuinixam"
author = "cuinixam"
release = "0.1.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

# https://github.com/executablebooks/sphinx-design
extensions.append("sphinx_design")

# https://myst-parser.readthedocs.io/en/latest/intro.html
extensions.append("myst_parser")

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "html_admonition",
    "html_image",
]

# TODO: enable this extension when is is supported by readthedocs
# draw.io config - @see https://pypi.org/project/sphinxcontrib-drawio/
# extensions.append("sphinxcontrib.drawio")
# drawio_default_transparency = True

# mermaid config - @see https://pypi.org/project/sphinxcontrib-mermaid/
extensions.append("sphinxcontrib.mermaid")

# Configure extensions for include doc-strings from code
extensions.extend(
    [
        "sphinx.ext.autodoc",
        "sphinx.ext.autosummary",
        "sphinx.ext.napoleon",
        "sphinx.ext.viewcode",
    ]
)

# mlx.traceability config - https://pypi.org/project/mlx-traceability/
extensions.append("mlx.traceability")

# Make relationship like 'validated_by' be shown for each requirement
traceability_render_relationship_per_item = True

# The suffix of source filenames.
source_suffix = [
    ".rst",
    ".md",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# copy button for code block
extensions.append("sphinx_copybutton")

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_book_theme"
html_logo = "_static/clanguru-logo.png"
html_favicon = "_static/clanguru-logo.png"
html_theme_options = {
    "home_page_in_toc": True,
    "github_url": "https://github.com/cuinixam/clanguru",
    "repository_url": "https://github.com/cuinixam/clanguru",
    "repository_branch": "main",
    "path_to_docs": "docs",
    "use_repository_button": True,
    "use_edit_page_button": True,
    "use_issues_button": True,
    "navigation_with_keys": False,
}
html_last_updated_fmt = ""
html_static_path = [
    os.path.join(os.path.dirname(mlx.traceability.__file__), "assets"),
    "_static",
]
