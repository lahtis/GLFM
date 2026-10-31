# src/glfm/loaders/__init__.py
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.1.0
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
"""
GLFM data source loaders.

Each loader reads one data source and returns a structured dict.
"""

__all__ = [
    "load_cldr_likely_subtags",
    "load_glottolog",
    "load_iso_639",
    "load_override_scripts",
    "load_pos_stats",
    "load_uralic_languages",
    "load_wiktionary_languages",
    "load_written_languages",
]
