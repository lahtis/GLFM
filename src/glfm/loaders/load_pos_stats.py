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
from typing import Any, Dict

from glfm.paths import get_data_dir

log = logging.getLogger(__name__)


def _load_iso1_to_iso3() -> Dict[str, str]:
    """Load ISO 639-1 -> ISO 639-3 mapping from data/iso_639_1.py.

    The file contains a single flat dict:
        iso_639_1 = {"fi": "fin", "en": "eng", ...}
    """
    iso1_path = get_data_dir() / "iso_639_1.py"
    if not iso1_path.exists():
        log.info("iso_639_1.py not found (%s)", iso1_path)
        return {}

    try:
        code = iso1_path.read_text(encoding="utf-8")
        namespace: Dict[str, Any] = {}
        exec(compile(code, str(iso1_path), "exec"), namespace)
    except (OSError, SyntaxError) as e:
        log.warning("Could not load iso_639_1.py: %s", e)
        return {}

    iso1_data = namespace.get("iso_639_1", {})
    if not isinstance(iso1_data, dict):
        log.warning("iso_639_1 is not a dict — skipping remap")
        return {}

    mapping: Dict[str, str] = {}
    for iso1, iso3 in iso1_data.items():
        if (
            isinstance(iso1, str)
            and len(iso1) == 2
            and isinstance(iso3, str)
            and len(iso3) == 3
        ):
            mapping[iso1] = iso3
    return mapping


def _remap_pos_stats(
    stats: Dict[str, Dict[str, int]],
    iso1_to_iso3: Dict[str, str],
) -> Dict[str, Dict[str, int]]:
    if not iso1_to_iso3:
        return stats

    remapped: Dict[str, Dict[str, int]] = {}
    for key, value in stats.items():
        target = iso1_to_iso3.get(key, key)
        if target in remapped:
            for pos, count in value.items():
                remapped[target][pos] = (
                    remapped[target].get(pos, 0) + count
                )
        else:
            remapped[target] = dict(value)
    return remapped


def load_pos_stats() -> Dict[str, Dict[str, int]]:
    data_path = get_data_dir() / "pos_stats.json"

    if not data_path.exists():
        log.info("pos_stats.json missing (%s)", data_path)
        return {}

    try:
        with data_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        log.warning("Could not read pos_stats.json: %s", e)
        return {}

    if not isinstance(data, dict):
        log.warning(
            "pos_stats.json is not a dict (%s)",
            type(data).__name__,
        )
        return {}

    iso1_to_iso3 = _load_iso1_to_iso3()
    remapped = _remap_pos_stats(data, iso1_to_iso3)

    log.info(
        "Loaded POS stats for %d languages (remapped %d ISO 639-1 keys)",
        len(remapped), len(iso1_to_iso3),
    )
    return remapped
