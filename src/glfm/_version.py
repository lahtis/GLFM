# src/glfm/_version.py
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.1.0
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
"""
Single source of truth for the version.

Usage:
    from glfm._version import __version__
    from glfm._version import __version_tuple__

The version follows PEP 440:
    MAJOR.MINOR.PATCH[.devN | .aN | .bN | .rcN]
"""

import re

__version__ = "1.1.0"
__version_tuple__ = tuple(
    int(x) for x in re.findall(r"\d+", __version__)[:3]
)

# Optional: git commit, build date (can be updated in CI)
__build_date__ = "2026-10-31"
__git_commit__ = "unknown"
