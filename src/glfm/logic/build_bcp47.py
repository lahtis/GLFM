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


def build_bcp47(lang_id, script, region, iso_info):
    """Build a BCP-47 tag in the form: lang[-Script][-Region]

    Canonical casing (RFC 5646 §2.1.1):
      language = lowercase  (fi)
      script   = Titlecase  (Latn)
      region   = UPPERCASE  (FI)

    - Uses iso639_1 if available, otherwise lang_id
    - Does not add "UNKNOWN" or "001"
    - Filters empty values
    - strip() is checked AND used
    """
    lang = ((iso_info or {}).get("iso639_1") or lang_id).lower()
    parts = [lang]

    # Script -> Titlecase (Latn, Cyrl, Arab, ...)
    if script:
        s = script.strip()
        if s and s.upper() != "UNKNOWN":
            parts.append(s.capitalize())

    # Region -> UPPERCASE (FI, SE, DE, ...)
    if region:
        r = region.strip()
        if r and r.upper() not in ("UNKNOWN", "001"):
            parts.append(r.upper())

    return "-".join(parts)
