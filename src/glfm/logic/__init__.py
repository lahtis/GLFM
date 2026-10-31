# src/glfm/logic/__init__.py
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.1.0
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
"""
GLFM logic modules.

Decision logic for scripts, regions, fallbacks, and BCP-47.
"""

__all__ = [
    "build_bcp47",
    "decide_default_region",
    "decide_default_script",
    "decide_fallback",
    "is_uralic",
    "resolve_cldr_key",
    "set_uralic_langs",
]
