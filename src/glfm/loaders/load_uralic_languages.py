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
from pathlib import Path
from typing import Any, Set

from glfm.paths import get_bundled_data_dir

log = logging.getLogger(__name__)


def _load_json(path: Path) -> Any:
    """Load a JSON file or return None if it does not exist."""
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        log.warning("%s could not be read: %s", path.name, e)
        return None


def load_uralic_languages() -> Set[str]:
    """Load the set of Uralic languages (data/uralic_languages.json).

    Accepts two formats:
      - list:  ["fin", "hun", "sme", ...]
      - dict:  {"languages": ["fin", "hun", ...]}

    Always returns a set (empty if the file is missing or invalid).
    """
    uralic_file = get_bundled_data_dir() / "uralic_languages.json"
    data = _load_json(uralic_file)

    if data is None:
        log.info(
            "uralic_languages.json missing - uralicNLP=False for all"
        )
        return set()

    if isinstance(data, list):
        result = {str(x) for x in data if x}
        log.info("Loaded %d Uralic languages (list)", len(result))
        return result

    if isinstance(data, dict):
        langs = data.get("languages", [])
        if isinstance(langs, list):
            result = {str(x) for x in langs if x}
            log.info(
                "Loaded %d Uralic languages (dict)", len(result)
            )
            return result
        log.warning(
            "uralic_languages.json: 'languages' is not a list"
        )
        return set()

    log.warning(
        "uralic_languages.json: unknown type (%s)",
        type(data).__name__,
    )
    return set()
