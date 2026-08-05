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
import sys

try:
    import msgpack
except ImportError:
    print(
        "Virhe: 'msgpack'-pakettia ei ole asennettu. Asenna se suorittamalla: pip install msgpack"
    )
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_JSON = BASE_DIR / "output" / "unified" / "languages_top5.json"
OUTPUT_MSGPACK = BASE_DIR / "output" / "unified" / "languages_top5.msgpack"


def convert_json_to_msgpack():
    if not INPUT_JSON.exists():
        print(f"Virhe: Tiedostoa {INPUT_JSON} ei löydy! Aja ensin tools/build_top5.py.")
        return

    print(f"Luetaan syötettä: {INPUT_JSON}")
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Pakataan MessagePack-muotoon: {OUTPUT_MSGPACK}")
    # use_bin_type=True varmistaa tehokkaan binaarimuotoilun
    packed_bytes = msgpack.packb(data, use_bin_type=True)

    OUTPUT_MSGPACK.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_MSGPACK, "wb") as f:
        f.write(packed_bytes)

    json_size = INPUT_JSON.stat().st_size / (1024 * 1024)
    msgpack_size = OUTPUT_MSGPACK.stat().st_size / (1024 * 1024)
    reduction = (1 - (msgpack_size / json_size)) * 100

    print(f"\n--- PAKKAUSTESTIN TULOKSET ---")
    print(f"JSON-tiedoston koko:      {json_size:.2f} MB")
    print(f"MessagePack-tiedoston koko: {msgpack_size:.2f} MB")
    print(f"Koon pieneneminen:          {reduction:.1f} %")


if __name__ == "__main__":
    convert_json_to_msgpack()
