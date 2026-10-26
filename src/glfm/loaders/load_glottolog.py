#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.0.2
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#

import json
import logging
from pathlib import Path

from glfm.paths import get_data_dir, get_output_dir
from typing import Any, Dict

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA = get_data_dir() / "glottolog.json"


def _coord(v) -> float | None:
    """Normalisoi koordinaatti floatiksi tai Noneksi."""
    try:
        return float(v) if v is not None else None
    except (ValueError, TypeError):
        return None


def load_glottolog() -> Dict[str, Dict[str, Any]]:
    """
    Lataa Glottolog-metadatan ja palauttaa sen jäsenneltynä sanakirjana.

    Avaimena on ISO 639-3 -koodi (esim. "fin"), ei glottocode.
    Palautettu rakenne jokaiselle kielelle:
        {
            "glottocode": "finn1318",
            "iso639_3": "fin",
            "family": "Finnic",         # Glottologin nimi, ei ISO 639-5 -koodi
            "macroarea": "Eurasia",
            "latitude": 60.5,
            "longitude": 25.0,
            "lineage": [...],
            "status": "...",
        }
    """
    if not DATA.exists():
        log.warning("glottolog.json puuttuu: %s", DATA)
        return {}

    with DATA.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, dict):
        log.error("glottolog.json ei ole dict, vaan %s", type(raw).__name__)
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

    log.info("Ladattu %d kielen Glottolog-metadata", len(glotto))
    return glotto
