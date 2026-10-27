#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.0.5
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#

import json
import logging
from pathlib import Path
from typing import Any, Dict

from glfm.paths import get_data_dir

log = logging.getLogger(__name__)

DATA = get_data_dir() / "wiktionary_languages.json"


def load_wiktionary_languages() -> Dict[str, Any]:
    """
    Load Wiktionary language metadata (data/wiktionary_languages.json).

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

    The file is optional – if missing, an empty dict is returned.
    """
    if not DATA.exists():
        log.info("wiktionary_languages.json missing (%s) – skipping", DATA)
        return {}

    try:
        with DATA.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        log.warning("wiktionary_languages.json not readable: %s", e)
        return {}

    if not isinstance(data, dict):
        log.warning("wiktionary_languages.json is not a dict (%s) – skipping",
                    type(data).__name__)
        return {}

    log.info("Loaded Wiktionary metadata for %d languages", len(data))
    return data
