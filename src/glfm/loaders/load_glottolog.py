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

from glfm.errors import DataError, OperationalError
from glfm.paths import get_data_dir

log = logging.getLogger(__name__)


def _coord(v) -> float | None:
    """Normalize a coordinate to float or None."""
    try:
        return float(v) if v is not None else None
    except (ValueError, TypeError):
        return None


def load_glottolog() -> Dict[str, Dict[str, Any]]:
    """Load Glottolog metadata as a structured dict.

    Keyed by ISO 639-3 code (e.g. "fin"), not glottocode.
    Structure per language:
        {
            "glottocode": "finn1318",
            "iso639_3": "fin",
            "family": "Finnic",      # Glottolog name, not ISO 639-5 code
            "macroarea": "Eurasia",
            "latitude": 60.5,
            "longitude": 25.0,
            "lineage": [...],
            "status": "...",
        }
    """
    data_path = get_data_dir() / "glottolog.json"

    if not data_path.exists():
        log.warning("glottolog.json missing: %s", data_path)
        return {}

    try:
        with data_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        raise DataError(
            f"Invalid JSON in {data_path}: {e}",
            source="glottolog.json",
        ) from e
    except OSError as e:
        raise OperationalError(
            f"Could not read {data_path}: {e}",
            source="filesystem",
            kind="transport",
        ) from e

    if not isinstance(raw, dict):
        log.error(
            "glottolog.json is not a dict, got %s",
            type(raw).__name__,
        )
        return {}

    glotto: Dict[str, Dict[str, Any]] = {}
    for code, info in raw.items():
        if not isinstance(info, dict):
            continue

        lineage = info.get("lineage")
        glotto[code] = {
            "glottocode": info.get("glottocode") or "",
            "iso639_3": info.get("iso639_3") or code,
            "family": info.get("family") or "",
            "macroarea": info.get("macroarea") or "",
            "latitude": _coord(info.get("latitude")),
            "longitude": _coord(info.get("longitude")),
            "lineage": lineage if isinstance(lineage, list) else [],
            "status": info.get("status") or "",
        }

    log.info("Loaded Glottolog metadata for %d languages", len(glotto))
    return glotto
