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
# Muuntaa JSON-tiedoston MessagePack-muotoon.
# HUOM: MessagePack ei ole jaettava muiden kielten kanssa ilman erillistä
# dekooderia – käytä .json.gz jos jaat dataa eteenpäin.
#

import argparse
import json
import logging
import sys
from pathlib import Path

from glfm.paths import get_data_dir, get_output_dir

try:
    import msgpack
except ImportError:
    print(
        "Virhe: 'msgpack'-pakettia ei ole asennettu.\n"
        "Asenna se: pip install msgpack",
        file=sys.stderr,
    )
    sys.exit(1)

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = get_output_dir() / "unified" / "languages_top20.json"
DEFAULT_OUTPUT = get_output_dir() / "unified" / "languages_top20.msgpack"


def convert_json_to_msgpack(input_path: Path, output_path: Path) -> dict:
    """
    Lukee JSON-tiedoston ja kirjoittaa sen MessagePack-muodossa.

    Palauttaa dictin, jossa on tiedostokoot tavuina.
    """
    if not input_path.exists():
        raise FileNotFoundError(
            f"Syöte puuttuu: {input_path}\n"
            f"Aja ensin: python3 tools/build_consumer_dataset.py"
        )

    log.info("Luetaan: %s", input_path)
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    log.info("Pakataan MessagePack-muotoon: %s", output_path)
    packed_bytes = msgpack.packb(data, use_bin_type=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(output_path.suffix + ".tmp")
    with open(tmp, "wb") as f:
        f.write(packed_bytes)
    tmp.replace(output_path)

    return {
        "input_size": input_path.stat().st_size,
        "output_size": output_path.stat().st_size,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Muunna JSON MessagePack-muotoon.",
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_INPUT,
        help=f"Syöte (oletus: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help=f"Tuloste (oletus: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        r = convert_json_to_msgpack(args.input, args.output)
    except FileNotFoundError as e:
        log.error("%s", e)
        return 1

    in_mb = r["input_size"] / (1024 * 1024)
    out_mb = r["output_size"] / (1024 * 1024)
    reduction = (1 - out_mb / in_mb) * 100 if in_mb > 0 else 0

    print()
    print("--- PAKKAUSTESTIN TULOKSET ---")
    print(f"JSON-tiedoston koko:        {in_mb:.2f} MB")
    print(f"MessagePack-tiedoston koko: {out_mb:.2f} MB")
    print(f"Koon pieneneminen:          {reduction:.1f} %")
    print()
    print(f"Tiedosto: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
