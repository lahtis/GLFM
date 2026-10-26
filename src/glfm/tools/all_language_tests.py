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

import argparse
import json
import logging
from collections import Counter
from pathlib import Path

from glfm.paths import get_data_dir, get_output_dir

log = logging.getLogger(__name__)

# --- Tiedostopolut ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = get_output_dir() / "unified" / "unified_languages.json"
OUTPUT_LANG_LIST = get_output_dir() / "unified" / "all_languages_list.json"
OUTPUT_ERRORS = get_output_dir() / "unified" / "validation_errors.json"


def validate(unified: dict) -> tuple[list[dict], list[dict]]:
    """
    Palauttaa (all_langs_list, errors).

    Puhdas funktio – ei tiedostokirjoituksia. Testattavissa pytest:llä.
    """
    errors: list[dict] = []
    all_langs_list: list[dict] = []

    for lang_id, lang in unified.items():
        entry = {
            "id": lang_id,
            "bcp47": lang.get("bcp47", ""),
            "default_script": lang.get("default_script", ""),
            "default_region": lang.get("default_region", ""),
            "written": bool(lang.get("written", False)),
            "written_scripts": lang.get("written_scripts", []),
            "uralicNLP": bool(lang.get("uralicNLP", False)),
        }
        all_langs_list.append(entry)

        ds = entry["default_script"]
        ws = entry["written_scripts"]
        bcp = entry["bcp47"]
        written = entry["written"]

        # --- Testi 1: written=True vaatii skriptin ---
        # (tyhjä skripti on OK ei-kirjoitetuille)
        if written and not ds:
            errors.append({
                "id": lang_id,
                "type": "written_but_no_script",
                "value": ds,
            })

        # --- Testi 1b: UNKNOWN on aina virhe (sentinel, ei arvo) ---
        if ds and ds.upper() == "UNKNOWN":
            errors.append({
                "id": lang_id,
                "type": "script_is_unknown_sentinel",
                "value": ds,
            })

        # --- Testi 2: ristiriita written-flagin ja skriptilistan välillä ---
        # (aiempi "default_script in written_scripts" oli kehäpäätelmä,
        #  koska written_scripts rakennetaan default_script:sta)
        if written and not ws:
            errors.append({
                "id": lang_id,
                "type": "written_but_empty_scripts",
                "value": ws,
            })
        if not written and ws:
            errors.append({
                "id": lang_id,
                "type": "not_written_but_has_scripts",
                "value": ws,
            })

        # --- Testi 3: written_scripts ei saa sisältää UNKNOWN ---
        for s in ws:
            if s.upper() == "UNKNOWN":
                errors.append({
                    "id": lang_id,
                    "type": "written_scripts_contains_unknown",
                    "value": ws,
                })
                break

        # --- Testi 4: BCP47 ei saa sisältää -UNKNOWN tai -001 ---
        if "-UNKNOWN" in bcp or "-001" in bcp:
            errors.append({
                "id": lang_id,
                "type": "bcp47_invalid_value",
                "value": bcp,
            })

        # --- Testi 5: default_region 001 ei saa näkyä BCP47:ssä ---
        # (build_bcp47 jo suodattaa tämän, mutta varmistetaan)
        region = entry["default_region"]
        if region == "001" and "-001" in bcp:
            errors.append({
                "id": lang_id,
                "type": "region_001_in_bcp47",
                "value": bcp,
            })

    return all_langs_list, errors


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
    tmp.replace(path)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(description="Validoi unified_languages.json")
    parser.add_argument("--input", type=Path, default=INPUT_FILE)
    parser.add_argument("--errors", type=Path, default=OUTPUT_ERRORS)
    parser.add_argument("--list", type=Path, default=OUTPUT_LANG_LIST)
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(
            f"Syöte puuttuu: {args.input}\n"
            f"Aja ensin: python3 build_unified.py"
        )

    log.info("Luetaan: %s", args.input)
    with open(args.input, "r", encoding="utf-8") as f:
        unified = json.load(f)

    all_langs, errors = validate(unified)

    save_json(args.list, all_langs)
    save_json(args.errors, errors)

    # Yhteenveto
    print(f"\nValidointi valmis: {len(unified)} kieltä tarkistettu")
    print(f"Virheitä: {len(errors)}")
    print(f"Kielilista: {args.list}")
    print(f"Virhelista: {args.errors}")

    if errors:
        # Virhetyyppien jakauma
        counts = Counter(e["type"] for e in errors)
        print(f"\nVirhetyypit:")
        for vtype, n in counts.most_common():
            print(f"  {vtype}: {n}")


if __name__ == "__main__":
    main()
