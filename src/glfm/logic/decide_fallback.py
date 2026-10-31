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


def decide_fallback(lang_id: str, wikt: dict | None) -> str:
    """Fallback logic:

    1. If Wiktionary defines a parent language -> use it
    2. Otherwise fallback is the language itself

    Always returns a valid language code (never empty).
    """
    if not isinstance(wikt, dict):
        return lang_id

    parent = wikt.get("parent")
    if not isinstance(parent, str):
        return lang_id

    parent = parent.strip().lower()
    if not parent or parent == "unknown":
        return lang_id

    return parent
