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

_URALIC_SET: set[str] = set()


def set_uralic_langs(lang_set) -> None:
    """Set the set of Uralic languages.

    Clears the previous set and replaces it with the new one.
    Accepts any iterable (set, list, dict_keys).
    """
    global _URALIC_SET
    if lang_set is None:
        _URALIC_SET = set()
        log.warning(
            "set_uralic_langs got None - uralicNLP=False for all"
        )
        return
    try:
        _URALIC_SET = set(lang_set)
        log.info("Set %d Uralic languages", len(_URALIC_SET))
    except TypeError as e:
        log.error(
            "set_uralic_langs: could not convert to set: %s", e
        )
        _URALIC_SET = set()


def is_uralic(lang_id: str) -> bool:
    """Is the language Uralic? (per-query, O(1))"""
    return lang_id in _URALIC_SET
