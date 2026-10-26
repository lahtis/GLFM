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
# Parsii ISO 639-2 -lähdetiedoston (iso-639-2.txt) JSON-muotoon.
#

import argparse
import json
import logging
import os
from pathlib import Path

from glfm.paths import get_data_dir, get_output_dir

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = get_data_dir()
DEFAULT_SRC = DATA_ROOT / "iso-639-2.txt"
DEFAULT_OUT = DATA_ROOT / "iso_639_2.json"


def parse_iso_639_2(src: Path) -> dict:
    """
    Parsii ISO 639-2 -lähdetiedoston.

    Rivimuoto: bcode|tcode|iso1|en_name|fr_name
    Palauttaa dictin avaimena 3-kirjaiminen koodi (T jos on, muuten B).
    """
    result: dict = {}
    skipped = 0

    with open(src, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split("|")
            if len(parts) < 5:
                log.debug("Ohitetaan rivi %d: liian vähän kenttiä", lineno)
                skipped += 1
                continue

            bcode, tcode, iso1, en_name, _fr_name = [p.strip() for p in parts[:5]]

            # 3-koodi: T-koodi jos on, muuten B-koodi
            code3 = tcode or bcode
            if not code3:
                skipped += 1
                continue

            result[code3] = {
                "name": en_name,
                "iso639_2B": bcode or "",
                "iso639_2T": tcode or "",
                "iso639_1": iso1 or "",
                "iso639_3": code3,
            }

    log.info("Parsittu %d koodia, ohitettu %d riviä", len(result), skipped)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Parsii ISO 639-2 -lähdetiedoston JSON-muotoon.",
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_SRC,
        help=f"Lähdetiedosto (oletus: {DEFAULT_SRC})",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUT,
        help=f"Tulostiedosto (oletus: {DEFAULT_OUT})",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Lähdetiedosto puuttuu: {args.input}")

    log.info("Luetaan: %s", args.input)
    result = parse_iso_639_2(args.input)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(args.output)

    log.info("Tallennettu: %s (%d koodia)", args.output, len(result))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )
    main()
