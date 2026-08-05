#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
#
# Licensed under the MIT License.
#

import argparse
import json
from pathlib import Path

# Suhteelliset polut projektin juureen nähden
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TOP_K = 5
INPUT_FILE = BASE_DIR / "output" / "unified" / "unified_languages.json"
EXTINCT_CONFIG_FILE = BASE_DIR / "data" / "extinct_languages.json"


def load_extinct_codes_fast(config_path: Path) -> set:
    """Lataa kuolleet koodit suoraan esikäsitellystä JSON-tiedostosta (nopea ja kevyt muistille)."""
    if not config_path.exists():
        print(f"Virhe: Tiedostoa {config_path} ei löydy. Aja ensin logic/build_extinct_json.py!")
        return set()

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        codes = set(data.get("codes", []))
        print(f"Ladattu {len(codes)} suodatettavaa koodia tiedostosta {config_path}.")
        return codes


def is_living_text_language(lang_data: dict, lang_code: str, extinct_codes: set) -> bool:
    """Tarkistaa automaattisesti, onko kieli elävä ja kirjoitettu kieli."""
    if not lang_data.get("written", False):
        return False

    if lang_code in extinct_codes:
        return False

    status = str(lang_data.get("status", "") or lang_data.get("type", "")).lower()
    if status in ["extinct", "historical", "ancient", "e", "h", "a"]:
        return False

    region = lang_data.get("default_region", "")
    has_iso1 = bool(lang_data.get("iso639_1"))

    if not has_iso1 and (not region or region == "001"):
        return False

    return True


def limit_json_neighbors(
    input_json_path: Path,
    output_json_path: Path,
    extinct_config_path: Path,
    top_k: int = DEFAULT_TOP_K,
):
    """Lukee GLFM-tutkimus-JSONin ja rajaa 'nearest_languages'-listat top_k elävään kirjoitettuun kieleen."""
    extinct_codes = load_extinct_codes_fast(extinct_config_path)

    print(f"Luetaan syötettä: {input_json_path} (Rajataan top {top_k} elävää kirjoitettua naapuria)")

    if not input_json_path.exists():
        print(f"Tiedostoa {input_json_path} ei löydy!")
        return

    with open(input_json_path, "r", encoding="utf-8") as f:
        full_data = json.load(f)

    limited_data = {}
    original_total = len(full_data)

    for lang_code, data in full_data.items():
        if not is_living_text_language(data, lang_code, extinct_codes):
            continue

        lang_entry = dict(data)
        raw_neighbors = data.get("nearest_languages", [])

        clean_neighbors = []
        for n in raw_neighbors:
            target_lang = n.get("lang")
            dist = n.get("distance", 1.0)

            if not target_lang or target_lang == lang_code:
                continue

            target_info = full_data.get(target_lang, {})
            if is_living_text_language(target_info, target_lang, extinct_codes):
                clean_neighbors.append({"lang": target_lang, "distance": dist})

            if len(clean_neighbors) >= top_k:
                break

        lang_entry["nearest_languages"] = clean_neighbors
        limited_data[lang_code] = lang_entry

    print(f"Kirjoitetaan rajattu JSON-tiedosto: {output_json_path}")
    output_json_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(limited_data, f, ensure_ascii=False, indent=2)

    in_size = input_json_path.stat().st_size / (1024 * 1024)
    out_size = output_json_path.stat().st_size / (1024 * 1024)

    print(f"\nValmis! Alkuperäisiä kieliä: {original_total}, eläviä kirjoitettuja kieliä jäljellä: {len(limited_data)}.")
    print(f"Alkuperäinen koko: {in_size:.2f} MB")
    print(f"Uusi rajattu koko (top {top_k} elävää naapuria): {out_size:.2f} MB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rajoita GLFM nearest_languages -lista eläviin kieliin.")
    parser.add_argument(
        "-k",
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help=f"Naapureiden enimmäismäärä (oletus: {DEFAULT_TOP_K})",
    )
    args = parser.parse_args()

    output_file = BASE_DIR / "output" / "unified" / f"languages_top{args.top_k}.json"

    limit_json_neighbors(
        INPUT_FILE,
        output_file,
        EXTINCT_CONFIG_FILE,
        top_k=args.top_k,
    )
