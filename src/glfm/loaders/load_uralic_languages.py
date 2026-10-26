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
from typing import Any, Set

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = get_bundled_data_dir()
URALIC_FILE = DATA_ROOT / "uralic_languages.json"


def _load_json(path: Path) -> Any:
    """Lataa JSON-tiedoston tai palauttaa tyhjän, jos ei ole olemassa."""
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        log.warning("%s ei luettavissa: %s", path.name, e)
        return None


def load_uralic_languages() -> Set[str]:
    """
    Lataa uralilaisten kielten joukon (data/uralic_languages.json).

    Hyväksyy kaksi muotoa:
      - lista:  ["fin", "hun", "sme", ...]
      - dict:   {"languages": ["fin", "hun", ...]}

    Palauttaa aina setin (tyhjä jos tiedosto puuttuu tai on virheellinen).
    """
    data = _load_json(URALIC_FILE)

    if data is None:
        log.info("uralic_languages.json puuttuu – uralicNLP=False kaikille")
        return set()

    if isinstance(data, list):
        result = {str(x) for x in data if x}
        log.info("Ladattu %d uralilaista kieltä (lista)", len(result))
        return result

    if isinstance(data, dict):
        langs = data.get("languages", [])
        if isinstance(langs, list):
            result = {str(x) for x in langs if x}
            log.info("Ladattu %d uralilaista kieltä (dict)", len(result))
            return result
        log.warning("uralic_languages.json: 'languages' ei ole lista")
        return set()

    log.warning("uralic_languages.json: tuntematon tyyppi (%s)",
                type(data).__name__)
    return set()
