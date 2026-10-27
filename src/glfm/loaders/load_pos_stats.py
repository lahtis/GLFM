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

from glfm.paths import get_data_dir
from typing import Any, Dict

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA = get_data_dir() / "pos_stats.json"


def load_pos_stats() -> Dict[str, Dict[str, int]]:
    """
    Lataa POS-tilastot (data/pos_stats.json).

    Palautettu rakenne:
        {"fi": {"noun": 12345, "verb": 6789, ...}, ...}

    Tiedosto on valinnainen – jos se puuttuu, palautetaan tyhjä dict.
    Tämä on normaalia: pos_stats generoidaan Wiktextractista, joka on
    iso (5–10 Gt) eikä ole mukana repossa.
    """
    if not DATA.exists():
        log.info("pos_stats.json puuttuu (%s) – POS-tilastot jäävät tyhjiksi",
                 DATA)
        return {}

    try:
        with DATA.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        log.warning("pos_stats.json ei luettavissa: %s", e)
        return {}

    if not isinstance(data, dict):
        log.warning("pos_stats.json ei ole dict (%s) – ohitetaan",
                    type(data).__name__)
        return {}

    log.info("Ladattu POS-tilastot %d kielelle", len(data))
    return data
