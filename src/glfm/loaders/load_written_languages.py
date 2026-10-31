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


def load_written_languages() -> Dict[str, Any]:
    """Load written-languages metadata.

    Reads data/written_languages.json.

    Returned structure (estimated):
        {
            "fin": {"scripts": ["Latn"], ...},
            ...
        }

    Filters out "UNKNOWN" and empty scripts from each language.
    The file is optional - if missing, an empty dict is returned.
    """
    data_path = get_data_dir() / "written_languages.json"

    if not data_path.exists():
        log.info(
            "written_languages.json missing (%s) - skipping",
            data_path,
        )
        return {}

    try:
        with data_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        log.warning(
            "written_languages.json not readable: %s", e
        )
        return {}

    if not isinstance(data, dict):
        log.warning(
            "written_languages.json is not a dict (%s) - skipping",
            type(data).__name__,
        )
        return {}

    # Clean scripts: remove "UNKNOWN" and empty values
    for lang_id, info in data.items():
        if not isinstance(info, dict):
            continue
        scripts = info.get("scripts", [])
        if isinstance(scripts, list):
            info["scripts"] = [
                s for s in scripts
                if s and isinstance(s, str)
                and s.upper() != "UNKNOWN"
            ]

    log.info("Loaded written metadata for %d languages", len(data))
    return data
