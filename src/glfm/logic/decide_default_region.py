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

from glfm.logic.resolve_cldr_key import resolve_cldr_key

log = logging.getLogger(__name__)


def decide_default_region(lang_id, wikt, cldr, iso_info):
    """Determine the default region (ISO 3166-1 alpha-2 or "001" = World):

    1. CLDR likelySubtags -> region  (fi-Latn-FI -> FI)
    2. Wiktionary -> region          (if present and not UNKNOWN)
    3. fallback: '001' (World)
    """
    # 1. CLDR
    cldr_key = resolve_cldr_key(lang_id, iso_info)
    tag = cldr.get(cldr_key) if isinstance(cldr, dict) else None
    if isinstance(tag, str):
        # CLDR uses '-' (e.g. fi-Latn-FI)
        parts = tag.split("-")
        if len(parts) >= 3:
            region = parts[2].strip()
            if region and region.upper() != "UNKNOWN":
                return region.upper()

    # 2. Wiktionary
    if wikt:
        region = wikt.get("region")
        if isinstance(region, str) and region.strip():
            region = region.strip()
            if region.upper() != "UNKNOWN":
                return region.upper()

    # 3. fallback
    return "001"
