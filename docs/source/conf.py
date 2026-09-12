# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# -- Project information -----------------------------------------------------

project = 'Crypto Trading Stack'
copyright = '2026, Ignacio Santiago Díaz Utrilla'
author = 'Ignacio Santiago Díaz Utrilla'
release = '0.1.0'

# -- General configuration ---------------------------------------------------

# Raíz del repositorio, para que autodoc pueda importar el paquete `src`.
sys.path.insert(0, os.path.abspath('../../'))

extensions = [
    'sphinx.ext.autodoc',    # Genera documentación a partir de los docstrings
    'sphinx.ext.napoleon',   # Soporta docstrings estilo Google/NumPy
    'sphinx.ext.mathjax',    # Renderiza las fórmulas (Avellaneda-Stoikov)
    'myst_parser',           # Permite incluir ficheros Markdown
]

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

templates_path = ['_templates']
exclude_patterns = []

language = 'es'

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
