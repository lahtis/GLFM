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


def decide_fallback(lang_id: str, wikt: dict | None) -> str:
    """
    Fallback-logiikka:

    1. Jos Wiktionary määrittää parent-kielen → käytä sitä
    2. Muuten fallback on kieli itse

    Palauttaa aina kelvollisen kielikoodin (ei tyhjää).
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
