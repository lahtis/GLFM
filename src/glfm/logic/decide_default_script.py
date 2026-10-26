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

import logging
import re

log = logging.getLogger(__name__)

# ISO 15924 Script -koodit: 4 kirjainta, ensimmäinen iso, loput pieniä (Latn, Cyrl, Arab)
SCRIPT_PATTERN = re.compile(r"^[A-Z][a-z]{3}$")

# ISO 15924 -erikoiskoodit, joita ei koskaan käytetä oletusskriptinä
SKIP_SCRIPTS = {"ZXXX", "ZYYY", "Zinh", "Zmth", "Zsye", "Zsym", "Zxxx"}


def _is_valid_script(s: str) -> bool:
    """Onko merkkijono kelvollinen ISO 15924 -skriptikoodi?"""
    if not s or not isinstance(s, str):
        return False
    if s.upper() == "UNKNOWN":
        return False
    if s in SKIP_SCRIPTS:
        return False
    return bool(SCRIPT_PATTERN.match(s))


def decide_default_script(lang_id, wikt, cldr, written, iso_info, overrides=None):
    """
    Päätetään kielen oletuskirjoitusjärjestelmä hierarkkisesti:

    1. Ohitustiedosto (data/override_scripts.json) – paikkaa CLDR:n aukot
    2. Written-languages -lähde
    3. CLDR likelySubtags
    4. Wiktionary
    5. Ei löytynyt → ""

    Palauttaa ISO 15924 -koodin (esim. "Latn") tai tyhjän merkkijonon.
    """
    overrides = overrides or {}

    # 1. Overrides
    if lang_id in overrides:
        val = overrides[lang_id]
        # Hyväksytään sekä lista että string
        candidates = val if isinstance(val, list) else [val]
        for s in candidates:
            if _is_valid_script(s):
                return s

    # 2. Written-languages
    if isinstance(written, dict):
        for s in written.get("scripts", []) or []:
            if _is_valid_script(s):
                return s

    # 3. CLDR likelySubtags
    if isinstance(cldr, dict):
        keys = [
            (iso_info or {}).get("iso639_1"),
            (iso_info or {}).get("iso639_3"),
            lang_id,
        ]
        for key in keys:
            if not key:
                continue
            tag = cldr.get(key)
            if not isinstance(tag, str):
                continue
            parts = tag.split("-")
            # Etsi BCP-47 osista ISO 15924 -muotoinen skripti
            for part in parts[1:]:
                if _is_valid_script(part):
                    return part.capitalize()

    # 4. Wiktionary
    if isinstance(wikt, dict):
        for s in wikt.get("scripts", []) or []:
            if _is_valid_script(s):
                return s

    return ""
