#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
#
# https://codeberg.org/lahtis/GLFM
#
# Licensed under the MIT License.
# You may obtain a copy of the License at:
# https://opensource.org/licenses/MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#


def decide_default_script(lang_id, wikt, cldr, written, iso_info, overrides=None):
    """
    Päätetään kielen oletuskirjoitusjärjestelmä hierarkkisesti:
    1. Ohitustiedosto (data/override_scripts.json) - paikkaa CLDR:n aukot
    2. Written-languages -lähde
    3. CLDR likelySubtags
    4. Wiktionary
    5. Ei löytynyt -> ""
    """
    overrides = overrides or {}

    # 1. Tarkistetaan täydentävä datalähde (overrides)
    if lang_id in overrides and overrides[lang_id]:
        return overrides[lang_id][0]

    # 2. Written-languages
    if written and written.get("scripts"):
        for s in written["scripts"]:
            if s and s.upper() != "UNKNOWN":
                return s

    # 3. CLDR likelySubtags
    cldr_keys = [iso_info.get("iso639_1"), iso_info.get("iso639_3"), lang_id]
    for key in cldr_keys:
        if key and key in cldr:
            tag = cldr[key]
            if isinstance(tag, str):
                parts = tag.split("-")
                if len(parts) >= 2 and parts[1].upper() != "UNKNOWN":
                    return parts[1]

    # 4. Wiktionary
    if wikt and wikt.get("scripts"):
        for s in wikt["scripts"]:
            if s and s.upper() != "UNKNOWN":
                return s

    return ""
