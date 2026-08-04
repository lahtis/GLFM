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

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class Language:
    """Unified language model used by the pipeline.

    Kaikki kentät ovat datavetoisia ja tulevat ISO/Wiktionary/CLDR/
    Written/Glottolog/POS-lähteistä.
    """

    # Perustunnisteet
    id: str
    name: str
    official_name: str

    # ISO-koodit
    iso639_1: str = ""
    iso639_2B: str = ""
    iso639_2T: str = ""
    iso639_3: str = ""
    iso639_5: str = ""

    # Oletusskripti ja -alue
    default_script: str = ""
    default_region: str = ""

    # BCP-47 tagi
    bcp47: str = ""

    # Fallback-kieli (murre → emo)
    fallback: str = ""

    # UralicNLP-tuki
    uralicNLP: bool = False

    # Written-languages metadata
    written: bool = False
    written_scripts: List[str] = field(default_factory=list)
    glottocode: str = ""
    family: str = ""

    # Glottolog-data
    glottolog: Dict[str, Any] = field(default_factory=dict)

    # POS-tilastot
    pos_stats: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Palauttaa datan puhdistettuna JSON-yhteensopivana dictinä."""
        return asdict(self)
