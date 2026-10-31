# src/glfm/tools/__init__.py
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.1.0
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
"""
GLFM tools.

Validators, reports, generators, and helper scripts.
Tools are run from the command line:

    python3 -m glfm.tools.<name>

For example:

    python3 -m glfm.tools.build_glottolog_json --wikidata
    python3 -m glfm.tools.build_consumer_dataset -k 20
    python3 -m glfm.tools.validate_bcp47
"""

__all__ = [
    # Producers
    "build_consumer_dataset",
    "build_glottolog_json",
    "build_iso_data",
    "build_pos_stats",
    "compute_nearest_languages",
    "convert_to_msgpack",
    "compress_stdlib",
    "download_wiktextract",
    "generate_iso_files",
    # Validators
    "validate_bcp47",
    "validate_fallbacks",
    "validate_glottolog",
    "validate_iso_consistency",
    "validate_pos_stats",
    # Reports / viz
    "generate_report",
    "visualize_fallbacks",
]
