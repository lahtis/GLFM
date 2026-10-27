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
DATA = get_data_dir() / "written_languages.json"


def load_written_languages() -> Dict[str, Any]:
    """
    Lataa kirjoitettujen kielten metadatan (data/written_languages.json).

    Palautettu rakenne (arvioitu):
        {
            "fin": {"scripts": ["Latn"], ...},
            ...
        }

    Suodattaa "UNKNOWN"- ja tyhjät skriptit jokaisesta kielestä.
    Tiedosto on valinnainen – jos se puuttuu, palautetaan tyhjä dict.
    """
    if not DATA.exists():
        log.info("written_languages.json puuttuu (%s) – ohitetaan", DATA)
        return {}

    try:
        with DATA.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        log.warning("written_languages.json ei luettavissa: %s", e)
        return {}

    if not isinstance(data, dict):
        log.warning("written_languages.json ei ole dict (%s) – ohitetaan",
                    type(data).__name__)
        return {}

    # Puhdista skriptit: poista "UNKNOWN" ja tyhjät
    for lang_id, info in data.items():
        if not isinstance(info, dict):
            continue
        scripts = info.get("scripts", [])
        if isinstance(scripts, list):
            info["scripts"] = [
                s for s in scripts
                if s and isinstance(s, str) and s.upper() != "UNKNOWN"
            ]

    log.info("Ladattu %d kielen written-metadata", len(data))
    return data
