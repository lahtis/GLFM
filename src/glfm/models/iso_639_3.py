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
# Rakentaa ISO 639-1/2/3 -JSON-tiedostot SIL:n iso-639-3.tab-tiedostosta.
#
# HUOM: Nämä .json-tiedostot EIVÄT ole käytössä load_iso_639.py:ssä,
# joka lukee .py-moduuleja (data/iso_639_*.py). Tämä on erillinen työkalu.
#

import argparse
import csv
import json
import logging
import os
from pathlib import Path

from glfm.paths import get_data_dir

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = get_data_dir()
DEFAULT_TAB = DATA_ROOT / "iso_639_3.tab"
DEFAULT_ISO3 = DATA_ROOT / "iso_639_3.json"
DEFAULT_ISO2 = DATA_ROOT / "iso_639_2.json"
DEFAULT_ISO1 = DATA_ROOT / "iso_639_1.json"


def _atomic_write_json(path: Path, data: dict) -> None:
    """Atominen JSON-kirjoitus."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def build_iso_data(tab: Path) -> tuple[dict, dict, dict]:
    """
    Lukee SIL:n iso-639-3.tab-tiedoston ja palauttaa kolme dictiä:
    (iso1, iso2, iso3).
    """
    iso1: dict = {}
    iso2: dict = {}
    iso3: dict = {}

    with open(tab, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            code3 = (row.get("Id") or "").strip()
            if not code3:
                continue

            part2b = (row.get("Part2B") or "").strip()
            part2t = (row.get("Part2T") or "").strip()
            part1 = (row.get("Part1") or "").strip()
            name = (row.get("Ref_Name") or "").strip()

            # ISO 639-3
            iso3[code3] = {
                "name": name,
                "iso639_3": code3,
                "iso639_2B": part2b,
                "iso639_2T": part2t,
                "iso639_1": part1,
            }

            # ISO 639-2
            if part2b or part2t:
                iso2[code3] = {
                    "name": name,
                    "iso639_2B": part2b,
                    "iso639_2T": part2t,
                    "iso639_1": part1,
                    "iso639_3": code3,
                }

            # ISO 639-1
            if part1:
                iso1[part1] = {
                    "name": name,
                    "iso639_1": part1,
                    "iso639_3": code3,
                }

    log.info("ISO 639-3: %d, ISO 639-2: %d, ISO 639-1: %d",
             len(iso3), len(iso2), len(iso1))
    return iso1, iso2, iso3


def main():
    parser = argparse.ArgumentParser(
        description="Rakenna ISO 639-1/2/3 JSON-tiedostot SIL .tab:sta.",
    )
    parser.add_argument(
        "--tab", type=Path, default=DEFAULT_TAB,
        help=f"SIL .tab-tiedosto (oletus: {DEFAULT_TAB})",
    )
    parser.add_argument(
        "--iso3", type=Path, default=DEFAULT_ISO3,
        help=f"ISO 639-3 JSON (oletus: {DEFAULT_ISO3})",
    )
    parser.add_argument(
        "--iso2", type=Path, default=DEFAULT_ISO2,
        help=f"ISO 639-2 JSON (oletus: {DEFAULT_ISO2})",
    )
    parser.add_argument(
        "--iso1", type=Path, default=DEFAULT_ISO1,
        help=f"ISO 639-1 JSON (oletus: {DEFAULT_ISO1})",
    )
    args = parser.parse_args()

    if not args.tab.exists():
        raise SystemExit(f"Lähdetiedosto puuttuu: {args.tab}")

    log.info("Luetaan: %s", args.tab)
    iso1, iso2, iso3 = build_iso_data(args.tab)

    _atomic_write_json(args.iso3, iso3)
    _atomic_write_json(args.iso2, iso2)
    _atomic_write_json(args.iso1, iso1)

    log.info("Tallennettu: %s, %s, %s", args.iso3, args.iso2, args.iso1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )
    main()
