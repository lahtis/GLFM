# src/glfm/__init__.py
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.1.0
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
"""
GLFM - Global Language Family Mapper

Language metadata database and tools for 7900+ languages (ISO 639-3).

Single source of truth for the version: _version.py
"""

from glfm._version import __version__, __version_tuple__

__all__ = ["__version__", "__version_tuple__"]
