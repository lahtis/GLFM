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
DATA = get_data_dir() / "wiktionary_languages.json"


def load_wiktionary_languages() -> Dict[str, Any]:
    """
    Lataa Wiktionary-kielimetadatan (data/wiktionary_languages.json).

    Palautettu rakenne (arvioitu):
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

    Tiedosto on valinnainen – jos se puuttuu, palautetaan tyhjä dict.
    """
    if not DATA.exists():
        log.info("wiktionary_languages.json puuttuu (%s) – ohitetaan", DATA)
        return {}

    try:
        with DATA.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        log.warning("wiktionary_languages.json ei luettavissa: %s", e)
        return {}

    if not isinstance(data, dict):
        log.warning("wiktionary_languages.json ei ole dict (%s) – ohitetaan",
                    type(data).__name__)
        return {}

    log.info("Ladattu %d kielen Wiktionary-metadata", len(data))
    return data
