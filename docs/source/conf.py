# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Realtime Dashboard'
copyright = '2026, Ignacio Santiago Díaz Utrilla'
author = 'Ignacio Santiago Díaz Utrilla'
release = 'February 2026'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ['_templates']
exclude_patterns = []

language = 'Spanish'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

import os
import sys
# 1. Ruta al core del proyecto (Golden Rules: acceso directo al código)
sys.path.insert(0, os.path.abspath('../../'))

# 2. Extensiones necesarias
extensions = [
    'sphinx.ext.autodoc',    # Genera doc desde docstrings
    'sphinx.ext.napoleon',   # Soporta estilo Google/NumPy
    'sphinx.ext.mathjax',    # Renderiza tus fórmulas (Avellaneda-Stoikov)
    'myst_parser',           # Lee tu README.md
]

# 3. Soporte para Markdown
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# 4. Tema visual (opcional pero profesional para Goldman Stanley)
html_theme = 'sphinx_rtd_theme'
