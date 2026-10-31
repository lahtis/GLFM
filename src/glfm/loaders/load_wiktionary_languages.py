#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.1.0
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#

import json
import logging
from typing import Any, Dict

from glfm.paths import get_data_dir

log = logging.getLogger(__name__)


def load_wiktionary_languages() -> Dict[str, Any]:
    """Load Wiktionary language metadata.

    Reads data/wiktionary_languages.json.

    Returned structure (estimated):
        {
            "fin": {
                "name": "Finnish",
                "official_name": "...",
                "region": "FI",
                "scripts": ["Latn"],
                "parent": "...",
                ...
            },
            ...
        }

    The file is optional - if missing, an empty dict is returned.
    """
    data_path = get_data_dir() / "wiktionary_languages.json"

    if not data_path.exists():
        log.info(
            "wiktionary_languages.json missing (%s) - skipping",
            data_path,
        )
        return {}

    try:
        with data_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        log.warning(
            "wiktionary_languages.json not readable: %s", e
        )
        return {}

    if not isinstance(data, dict):
        log.warning(
            "wiktionary_languages.json is not a dict (%s) - skipping",
            type(data).__name__,
        )
        return {}

    log.info(
        "Loaded Wiktionary metadata for %d languages", len(data)
    )
    return data
