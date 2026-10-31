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

import logging
import re

log = logging.getLogger(__name__)

# ISO 15924 script codes: 4 letters, first uppercase, rest lowercase
# (Latn, Cyrl, Arab).
SCRIPT_PATTERN = re.compile(r"^[A-Z][a-z]{3}$")

# ISO 15924 special codes that are never used as a default script.
SKIP_SCRIPTS = {"ZXXX", "ZYYY", "Zinh", "Zmth", "Zsye", "Zsym", "Zxxx"}


def _is_valid_script(s: str) -> bool:
    """Is the string a valid ISO 15924 script code?"""
    if not s or not isinstance(s, str):
        return False
    if s.upper() == "UNKNOWN":
        return False
    if s in SKIP_SCRIPTS:
        return False
    return bool(SCRIPT_PATTERN.match(s))


def decide_default_script(
    lang_id, wikt, cldr, written, iso_info, overrides=None
):
    """Determine the default script hierarchically:

    1. Override file (data/override_scripts.json) - fills CLDR gaps
    2. Written-languages source
    3. CLDR likelySubtags
    4. Wiktionary
    5. Not found -> ""

    Returns an ISO 15924 code (e.g. "Latn") or an empty string.
    """
    overrides = overrides or {}

    # 1. Overrides
    if lang_id in overrides:
        val = overrides[lang_id]
        # Accept both list and string
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
            # Find an ISO 15924-shaped script in the BCP-47 parts
            for part in parts[1:]:
                if _is_valid_script(part):
                    return part.capitalize()

    # 4. Wiktionary
    if isinstance(wikt, dict):
        for s in wikt.get("scripts", []) or []:
            if _is_valid_script(s):
                return s

    return ""
