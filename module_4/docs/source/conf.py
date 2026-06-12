import os
import sys

# Let autodoc find the src modules
sys.path.insert(0, os.path.abspath("../../src"))

project = "Grad Cafe Analytics"
author = "Your Name"
release = "1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

html_theme = "sphinx_rtd_theme"
templates_path = ["_templates"]
exclude_patterns = []
autodoc_member_order = "bysource"
