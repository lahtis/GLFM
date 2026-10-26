#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.0.4
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#

import gzip
import json
import logging
from pathlib import Path
from typing import Any, Dict

from glfm.loaders.load_iso_639 import load_iso_639
from glfm.loaders.load_cldr_likely_subtags import load_cldr_likely_subtags
from glfm.loaders.load_wiktionary_languages import load_wiktionary_languages
from glfm.loaders.load_uralic_languages import load_uralic_languages
from glfm.loaders.load_written_languages import load_written_languages
from glfm.loaders.load_glottolog import load_glottolog
from glfm.loaders.load_pos_stats import load_pos_stats
from glfm.loaders.load_override_scripts import load_override_scripts

from glfm.logic.decide_default_script import decide_default_script
from glfm.logic.decide_default_region import decide_default_region
from glfm.logic.build_bcp47 import build_bcp47
from glfm.logic.decide_fallback import decide_fallback
from glfm.logic.is_uralic import is_uralic
from glfm.logic.set_uralic_langs import set_uralic_langs

from glfm.models.language import Language
from glfm.paths import get_output_dir

log = logging.getLogger(__name__)

# ---------------------------------------------------------
# ETÄISYYS- JA LÄHDEMETATIEDOT (URIEL / lang2vec)
# ---------------------------------------------------------
DISTANCE_SOURCE = "lang2vec / URIEL"
DISTANCE_TYPE = "fam"
DISTANCE_BASES = ["WALS", "SSWL", "PHOIBLE", "Ethnologue", "Glottolog"]

# ---------------------------------------------------------
# OUTPUT-kansiot (glfm.paths:stä)
# ---------------------------------------------------------

OUTPUT_ROOT = get_output_dir()

SUBFOLDERS = ["unified", "validation", "dialects", "final", "logs"]

OUTPUT = OUTPUT_ROOT / "unified" / "unified_languages.json"
OUTPUT_GZ = OUTPUT_ROOT / "unified" / "unified_languages.json.gz"


def _ensure_dirs() -> None:
    """Luo output-kansiot. Kutsutaan main():sta, ei importin aikana."""
    for folder in SUBFOLDERS:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)


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

    if not uralic_set:
        log.warning("uralic_languages.json puuttuu tai on tyhjä – "
                    "kaikki uralicNLP-flagit ovat False")

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
        language_type = iso_info.get("language_type", "")

        # --- Skripti ja alue dynaamisesti lähteistä ---
        script = decide_default_script(lang_id, w, cldr, w_written, iso_info, overrides)
        region = decide_default_region(lang_id, w, cldr, iso_info)

        # --- Kirjoitetun kielen tila määräytyy YKSINOMAAN todennetusta skriptistä ---
        is_written_flag = bool(script and script.upper() != "UNKNOWN")
        scripts = [script] if is_written_flag else []

        # --- BCP-47 ---
        bcp47 = build_bcp47(lang_id, script if is_written_flag else "", region, iso_info)

        # --- Fallback ja Uralic-tuki ---
        fallback = decide_fallback(lang_id, w)
        uralic = is_uralic(lang_id)

        # --- Glottolog-kentät ---
        glottocode = (glotto.get("glottocode")
                      or w_written.get("glottocode", ""))
        family = (glotto.get("family")
                  or w_written.get("family", ""))

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
            language_type=language_type,
            default_script=script if is_written_flag else "",
            default_region=region,
            bcp47=bcp47,
            fallback=fallback,
            uralicNLP=uralic,
            written=is_written_flag,
            written_scripts=scripts,
            glottocode=glottocode,
            family=family,
            glottolog=glotto,
            pos_stats=pos,
        )

        lang_dict = lang_obj.__dict__

        # --- Etäisyysmetatiedot: AINA läsnä ---
        lang_dict["distance_source"] = DISTANCE_SOURCE
        lang_dict["distance_type"] = DISTANCE_TYPE
        lang_dict["distance_bases"] = DISTANCE_BASES
        lang_dict["nearest_languages"] = []

        unified[lang_id] = lang_dict

    return unified


# ---------------------------------------------------------
# Tallennus
# ---------------------------------------------------------

def _save(unified: Dict[str, Any]) -> None:
    """Tallentaa sekä pretty-JSON (debug) että gzip-JSON (tuotanto)."""
    # Pretty (debug, gitignoressa)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(unified, f, ensure_ascii=False, indent=2)
    log.info("Kirjoitettu: %s (%.1f MB)",
             OUTPUT, OUTPUT.stat().st_size / 1e6)

    # Gzip (tuotanto, pieni)
    with gzip.open(OUTPUT_GZ, "wt", encoding="utf-8") as f:
        json.dump(unified, f, ensure_ascii=False, separators=(",", ":"))
    log.info("Kirjoitettu: %s (%.1f MB)",
             OUTPUT_GZ, OUTPUT_GZ.stat().st_size / 1e6)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    _ensure_dirs()
    unified = build_unified()
    _save(unified)
    log.info("Valmis: %d kieltä", len(unified))


if __name__ == "__main__":
    main()
