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

import json
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UNIFIED = PROJECT_ROOT / "output" / "unified" / "unified_languages.json"

# Korjattu BCP-47 pattern:
# - Kieli: 2-3 kirjainta (pakollinen)
# - Script: -Latn, -Cyrl jne. (valinnainen)
# - Region: -FI, -GH, -001 jne. (valinnainen)
BCP47_PATTERN = re.compile(
    r"^[a-z]{2,3}(-[A-Z][a-z]{3})?(-([A-Z]{2}|\d{3}))?$",
    re.IGNORECASE
)

def validate_bcp47():
    with open(UNIFIED, "r", encoding="utf-8") as f:
        data = json.load(f)

    errors = []

    for lang_id, info in data.items():
        tag = info.get("bcp47")
        if not tag:
            continue

        if not BCP47_PATTERN.match(tag):
            errors.append(f"{lang_id}: invalid bcp47 '{tag}'")

    if errors:
        print("BCP-47 validation FAILED")
        for e in errors:
            print("  ", e)
    else:
        print("BCP-47 validation OK")


if __name__ == "__main__":
    validate_bcp47()
