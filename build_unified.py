#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
#
# Version 1.0.1
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
from typing import Dict, Any

from loaders.load_iso_639 import load_iso_639
from loaders.load_cldr_likely_subtags import load_cldr_likely_subtags
from loaders.load_wiktionary_languages import load_wiktionary_languages
from loaders.load_uralic_languages import load_uralic_languages
from loaders.load_written_languages import load_written_languages
from loaders.load_glottolog import load_glottolog
from loaders.load_pos_stats import load_pos_stats
from loaders.load_override_scripts import load_override_scripts

from logic.decide_default_script import decide_default_script
from logic.decide_default_region import decide_default_region
from logic.build_bcp47 import build_bcp47
from logic.decide_fallback import decide_fallback
from logic.is_uralic import is_uralic
from logic.set_uralic_langs import set_uralic_langs

from models.language import Language

# ---------------------------------------------------------
# ETÄISYYS- JA LÄHDEMETATIEDOT (URIEL / lang2vec)
# ---------------------------------------------------------
DISTANCE_SOURCE = "lang2vec / URIEL"
DISTANCE_TYPE = "genetic"
DISTANCE_BASES = ["WALS", "SSWL", "PHOIBLE", "Ethnologue", "Glottolog"]

# ---------------------------------------------------------
# OUTPUT-kansiot
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = PROJECT_ROOT / "output"

SUBFOLDERS = ["unified", "validation", "dialects", "final", "logs"]
for folder in SUBFOLDERS:
    (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)

OUTPUT = OUTPUT_ROOT / "unified" / "unified_languages.json"

# ---------------------------------------------------------
# Unified-rakenteen rakentaminen
# ---------------------------------------------------------

def build_unified() -> Dict[str, Any]:

    # --- Lataa datalähteet ---
    iso = load_iso_639()
    cldr = load_cldr_likely_subtags()
    wikt = load_wiktionary_languages()
    written = load_written_languages()
    uralic_set = load_uralic_languages()
    glottolog = load_glottolog()
    pos_stats = load_pos_stats()
    overrides = load_override_scripts()

    # --- Check uralic_languages.json ---
    if not uralic_set:
        print("Warning: uralic.json missing or empty. All languages will have uralicNLP=False")

    # Aseta uralilaiset kielet logic-moduulille
    set_uralic_langs(uralic_set)

    unified: Dict[str, Any] = {}

    # --- Käy läpi kaikki ISO-kielet ---
    for lang_id, iso_info in iso.items():

        w = wikt.get(lang_id, {})
        w_written = written.get(lang_id, {})
        glotto = glottolog.get(lang_id, {})
        pos = pos_stats.get(lang_id, {})

        # Nimet
        name = w.get("name") or iso_info.get("name") or lang_id
        official_name = w.get("official_name") or name

        # ISO-koodit
        iso1 = iso_info.get("iso639_1", "")
        iso2B = iso_info.get("iso639_2B", "")
        iso2T = iso_info.get("iso639_2T", "")
        iso3 = iso_info.get("iso639_3", "")
        iso5 = iso_info.get("iso639_5", "")

        # --- Skripti ja alue dynaamisesti lähteistä ---
        script = decide_default_script(lang_id, w, cldr, w_written, iso_info, overrides)
        region = decide_default_region(lang_id, w, cldr, iso_info)

        # --- Kirjoitetun kielen tila määräytyy YKSINOMAAN todennetusta skriptistä ---
        is_written_flag = bool(script and script.upper() != "UNKNOWN")

        # Kasataan kirjoitusskriptilista vain jos skripti on olemassa
        scripts = [script] if is_written_flag else []

        # --- BCP-47 ---
        bcp47 = build_bcp47(lang_id, script if is_written_flag else "", region, iso_info)

        # --- Fallback ja Uralic-tuki ---
        fallback = decide_fallback(lang_id, w)
        uralic = is_uralic(lang_id)

        # Luo Language-olio
        lang_obj = Language(
            id=lang_id,
            name=name,
            official_name=official_name,
            iso639_1=iso1,
            iso639_2B=iso2B,
            iso639_2T=iso2T,
            iso639_3=iso3,
            iso639_5=iso5,
            default_script=script if is_written_flag else "",
            default_region=region,
            bcp47=bcp47,
            fallback=fallback,
            uralicNLP=uralic,
            written=is_written_flag,
            written_scripts=scripts,
            glottocode=w_written.get("glottocode", "") if w_written else "",
            family=w_written.get("family", "") if w_written else "",
            glottolog=glotto,
            pos_stats=pos,
        )

        lang_dict = lang_obj.__dict__

        # --- Lisätään etäisyysmetatiedot vain todellisuudessa kirjoitetuille kielille ---
        if is_written_flag:
            lang_dict["distance_source"] = DISTANCE_SOURCE
            lang_dict["distance_type"] = DISTANCE_TYPE
            lang_dict["distance_bases"] = DISTANCE_BASES
            lang_dict["nearest_languages"] = []

        unified[lang_id] = lang_dict

    return unified

# ---------------------------------------------------------
# Tallennus
# ---------------------------------------------------------

def main() -> None:
    unified = build_unified()

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(unified, f, ensure_ascii=False, indent=2)

    print(f"Unified language database written to: {OUTPUT}")

if __name__ == "__main__":
    main()
