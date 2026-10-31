# src/glfm/models/__init__.py
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.1.0
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
"""
GLFM data models.

Contains the Language dataclass. The generated ISO modules
(iso_639_1, iso_639_2, iso_639_3, ...) live in the data directory,
not in this package.
"""

from glfm.models.language import Language

__all__ = ["Language"]
