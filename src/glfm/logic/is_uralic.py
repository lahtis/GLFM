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

_URALIC_SET: set[str] = set()


def set_uralic_langs(lang_set) -> None:
    """
    Asettaa uralilaisten kielten joukon.

    Tyhjentää aiemman joukon ja korvaa sen uudella.
    Hyväksyy minkä tahansa iteroitavan (set, list, dict_keys).
    """
    global _URALIC_SET
    if lang_set is None:
        _URALIC_SET = set()
        log.warning("set_uralic_langs sai None – uralicNLP=False kaikille")
        return
    try:
        _URALIC_SET = set(lang_set)
        log.info("Asetettu %d uralilaista kieltä", len(_URALIC_SET))
    except TypeError as e:
        log.error("set_uralic_langs: ei voi muuntaa setiksi: %s", e)
        _URALIC_SET = set()


def is_uralic(lang_id: str) -> bool:
    """Onko kieli uralilainen? (per‑kysely, O(1))"""
    return lang_id in _URALIC_SET
