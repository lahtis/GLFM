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

from glfm.paths import get_bundled_data_dir
from typing import Any, Dict

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA = get_bundled_data_dir() / "override_scripts.json"


def load_override_scripts() -> Dict[str, Any]:
    """
    Lataa manuaaliset skriptiohjitukset (data/override_scripts.json).

    Tiedosto on valinnainen – jos se puuttuu, palautetaan tyhjä dict.
    Palautettu rakenne:
        {"grc": ["Grek", "Linb"], "lat": ["Latn"], ...}
    """
    if not DATA.exists():
        log.info("override_scripts.json puuttuu (%s) – käytetään tyhjiä",
                 DATA)
        return {}

    try:
        with DATA.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        log.warning("override_scripts.json ei luettavissa: %s", e)
        return {}

    if not isinstance(data, dict):
        log.warning("override_scripts.json ei ole dict (%s) – ohitetaan",
                    type(data).__name__)
        return {}

    log.info("Ladattu %d skriptiohjitusta", len(data))
    return data
