#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM / Self-Healing Localization (SHL)
# Copyright (c) 2026 Tuomas Lähteenmäki
#
# Licensed under the MIT License.
#

import gzip
import json
from pathlib import Path
import pickle

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_JSON = BASE_DIR / "output" / "unified" / "languages_top20.json"

OUTPUT_GZ_JSON = BASE_DIR / "output" / "unified" / "languages_top20.json.gz"
OUTPUT_GZ_PKL = BASE_DIR / "output" / "unified" / "languages_top20.pkl.gz"


def test_stdlib_compression():
    if not INPUT_JSON.exists():
        print(f"Virhe: Tiedostoa {INPUT_JSON} ei löydy!")
        return

    # Luetaan alkuperäinen JSON
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Standard Gzip + JSON
    with gzip.open(OUTPUT_GZ_JSON, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(data, f, ensure_ascii=False)

    # 2. Standard Gzip + Pickle (Python optimoitu binaari vakiokirjastosta)
    with gzip.open(OUTPUT_GZ_PKL, "wb", compresslevel=9) as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

    json_mb = INPUT_JSON.stat().st_size / (1024 * 1024)
    gz_json_mb = OUTPUT_GZ_JSON.stat().st_size / (1024 * 1024)
    gz_pkl_mb = OUTPUT_GZ_PKL.stat().st_size / (1024 * 1024)

    print("--- STDLIB (0 DEPENDENCY) COMPRESSION RESULTS ---")
    print(f"Alkuperäinen JSON:            {json_mb:.2f} MB")
    print(
        f"Gzip JSON (.json.gz):         {gz_json_mb:.2f} MB ({gz_json_mb * 1024:.0f} KB)"
    )
    print(
        f"Gzip Pickle (.pkl.gz):        {gz_pkl_mb:.2f} MB ({gz_pkl_mb * 1024:.0f} KB)"
    )
    print(
        f"\nKoon säästö .json.gz:        {(1 - (gz_json_mb / json_mb)) * 100:.1f} %"
    )


if __name__ == "__main__":
    test_stdlib_compression()
