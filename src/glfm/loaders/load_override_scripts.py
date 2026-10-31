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

from glfm.paths import get_bundled_data_dir

log = logging.getLogger(__name__)


def load_override_scripts() -> Dict[str, Any]:
    """Load manual script overrides (data/override_scripts.json).

    The file is optional - if missing, an empty dict is returned.
    Structure:
        {"grc": ["Grek", "Linb"], "lat": ["Latn"], ...}
    """
    data_path = get_bundled_data_dir() / "override_scripts.json"

    if not data_path.exists():
        log.info(
            "override_scripts.json missing (%s) - using empty",
            data_path,
        )
        return {}

    try:
        with data_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        log.warning("Could not read override_scripts.json: %s", e)
        return {}

    if not isinstance(data, dict):
        log.warning(
            "override_scripts.json is not a dict (%s) - skipping",
            type(data).__name__,
        )
        return {}

    log.info("Loaded %d script overrides", len(data))
    return data
