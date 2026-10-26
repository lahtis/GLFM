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

    # SIL ISO 639-3 Language_Type:
    #   L = Living
    #   E = Extinct
    #   H = Historical
    #   A = Ancient
    #   C = Constructed
    #   "" = tuntematon
    language_type: str = ""

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
