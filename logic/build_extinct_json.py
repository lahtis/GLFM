#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
#
# Licensed under the MIT License.
#

import json
from pathlib import Path

# Suhteelliset polut projektin juureen nähden
BASE_DIR = Path(__file__).resolve().parent.parent
ISO_TAB_FILE = BASE_DIR / "data" / "iso_639_3.tab"
OUTPUT_JSON = BASE_DIR / "data" / "extinct_languages.json"


def generate_extinct_json():
    """Lukee ISO 639-3 .tab -tiedoston ja generoi kevyen JSON-tiedoston kuolleista kielistä."""
    extinct_codes = set()

    # 1. Poimitaan ISO 639-3 tab -tiedostosta E (Extinct), A (Ancient) ja H (Historical)
    if ISO_TAB_FILE.exists():
        print(f"Luetaan ISO-taulukkoa: {ISO_TAB_FILE}")
        with open(ISO_TAB_FILE, "r", encoding="utf-8") as f:
            f.readline()  # Ohitetaan otsikkorivi
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 6:
                    lang_id = parts[0].strip()
                    lang_type = parts[5].strip()
                    if lang_type in ("E", "A", "H"):
                        extinct_codes.add(lang_id)
        print(f"Löydetty {len(extinct_codes)} koodia ISO-taulukosta.")
    else:
        print(f"Varoitus: Tiedostoa {ISO_TAB_FILE} ei löytynyt!")

    # 2. Säilytetään myös käyttäjän aiemmat manuaaliset lisäykset (esim. 'lat'), jos tiedosto on jo olemassa
    if OUTPUT_JSON.exists():
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                old_codes = old_data.get("codes", [])
                extinct_codes.update(old_codes)
                print(f"Säilytetty {len(old_codes)} aiempaa manuaalista koodia JSON-tiedostosta.")
        except Exception as e:
            print(f"Huomio ladattaessa {OUTPUT_JSON}: {e}")

    sorted_codes = sorted(list(extinct_codes))

    data_to_save = {
        "description": "Esikäsitelty lista ISO 639-3 kuolleista/historiallisista kielistä sekä manuaalisista lisäyksistä.",
        "count": len(sorted_codes),
        "codes": sorted_codes,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)

    print(f"Valmis! Tallennettu yhteensä {len(sorted_codes)} kuollutta kielikoodia tiedostoon: {OUTPUT_JSON}")


if __name__ == "__main__":
    generate_extinct_json()
