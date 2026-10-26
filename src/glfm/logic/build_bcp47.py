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


def build_bcp47(lang_id, script, region, iso_info):
    """
    Rakentaa BCP-47 tagin muodossa: lang[-Script][-Region]

    Kanoninen kirjainkoko (RFC 5646 §2.1.1):
      language = lowercase  (fi)
      script   = Titlecase  (Latn)
      region   = UPPERCASE  (FI)

    - Käyttää iso639_1:tä jos löytyy, muuten lang_id
    - Ei lisää "UNKNOWN" tai "001"
    - Suodattaa tyhjät arvot
    - Strip() tarkistetaan JA käytetään
    """
    lang = ((iso_info or {}).get("iso639_1") or lang_id).lower()
    parts = [lang]

    # Script → Titlecase (Latn, Cyrl, Arab, ...)
    if script:
        s = script.strip()
        if s and s.upper() != "UNKNOWN":
            parts.append(s.capitalize())

    # Region → UPPERCASE (FI, SE, DE, ...)
    if region:
        r = region.strip()
        if r and r.upper() not in ("UNKNOWN", "001"):
            parts.append(r.upper())

    return "-".join(parts)
