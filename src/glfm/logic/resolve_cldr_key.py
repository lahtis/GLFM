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

log = logging.getLogger(__name__)


def resolve_cldr_key(lang_id: str, iso_info: dict | None) -> str:
    """CLDR uses ISO 639-1 codes whenever possible.

    If the language is ISO 639-3 (e.g. 'fin') and has an iso639_1
    ('fi'), the iso639_1 code is used for CLDR lookups.

    Always returns a non-empty string (lang_id as fallback).
    """
    if not isinstance(iso_info, dict):
        return lang_id

    iso1 = iso_info.get("iso639_1")
    if isinstance(iso1, str):
        iso1 = iso1.strip().lower()
        if iso1 and iso1 != "unknown":
            return iso1

    return lang_id
