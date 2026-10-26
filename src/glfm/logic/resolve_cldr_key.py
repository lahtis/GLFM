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

log = logging.getLogger(__name__)


def resolve_cldr_key(lang_id: str, iso_info: dict | None) -> str:
    """
    CLDR käyttää ISO 639-1 -koodeja aina kun mahdollista.

    Jos kieli on ISO 639-3 (esim. 'fin') ja sillä on iso639_1 ('fi'),
    käytetään CLDR-hakuihin iso639_1-koodia.

    Palauttaa aina ei-tyhjän merkkijonon (lang_id fallbackina).
    """
    if not isinstance(iso_info, dict):
        return lang_id

    iso1 = iso_info.get("iso639_1")
    if isinstance(iso1, str):
        iso1 = iso1.strip().lower()
        if iso1 and iso1 != "unknown":
            return iso1

    return lang_id
