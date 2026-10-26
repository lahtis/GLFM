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

import json
import logging
from pathlib import Path

from glfm.paths import get_data_dir, get_output_dir

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ISO_TAB_FILE = get_data_dir() / "iso_639_3.tab"
OUTPUT_JSON = get_data_dir() / "extinct_languages.json"

# SIL Language_Type -arvot, jotka lasketaan "kuolleiksi":
#   E = Extinct
#   A = Ancient
#   H = Historical
EXTINCT_TYPES = ("E", "A", "H")


def generate_extinct_json() -> None:
    """
    Lukee ISO 639-3 .tab -tiedoston ja generoi kevyen JSON-tiedoston
    kuolleista kielistä.

    Säilyttää aiemmat manuaaliset lisäykset (esim. 'lat'), jos tiedosto
    on jo olemassa.
    """
    extinct_codes: set[str] = set()

    # 1. Poimi E/A/H-koodit ISO 639-3 -taulukosta
    if ISO_TAB_FILE.exists():
        log.info("Luetaan ISO-taulukkoa: %s", ISO_TAB_FILE)
        with open(ISO_TAB_FILE, "r", encoding="utf-8") as f:
            f.readline()  # ohita otsikko
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 6:
                    lang_id = parts[0].strip()
                    lang_type = parts[5].strip()
                    if lang_id and lang_type in EXTINCT_TYPES:
                        extinct_codes.add(lang_id)
        log.info("Löydetty %d koodia ISO-taulukosta.", len(extinct_codes))
    else:
        log.warning("Tiedostoa %s ei löytynyt!", ISO_TAB_FILE)

    # 2. Säilytä aiemmat manuaaliset lisäykset
    if OUTPUT_JSON.exists():
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                old_data = json.load(f)
            old_codes = old_data.get("codes", [])
            if isinstance(old_codes, list):
                extinct_codes.update(old_codes)
                log.info("Säilytetty %d aiempaa manuaalista koodia.",
                         len(old_codes))
        except (json.JSONDecodeError, OSError, TypeError) as e:
            log.warning("Ei voitu lukea %s: %s", OUTPUT_JSON, e)

    sorted_codes = sorted(extinct_codes)

    data_to_save = {
        "description": (
            "Esikäsitelty lista ISO 639-3 kuolleista/historiallisista "
            "kielistä sekä manuaalisista lisäyksistä."
        ),
        "count": len(sorted_codes),
        "codes": sorted_codes,
    }

    # Atominen kirjoitus
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT_JSON.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    tmp.replace(OUTPUT_JSON)

    log.info("Valmis! Tallennettu %d kuollutta kielikoodia: %s",
             len(sorted_codes), OUTPUT_JSON)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )
    generate_extinct_json()
