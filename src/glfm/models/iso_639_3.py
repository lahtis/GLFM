#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.1.0
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
# Build ISO 639-1/2/3 JSON files from SIL's iso-639-3.tab.
#
# NOTE: These .json files are NOT used by load_iso_639.py, which reads
# .py modules (data/iso_639_*.py). This is a separate tool.
#

import argparse
import csv
import json
import logging
import os
from pathlib import Path

from glfm.errors import OperationalError
from glfm.paths import get_data_dir

log = logging.getLogger(__name__)


def _atomic_write_json(path: Path, data: dict) -> None:
    """Atomic JSON write."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                data, f,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)
    except OSError as e:
        raise OperationalError(
            f"Could not write {path}: {e}",
            source="filesystem",
            kind="transport",
        ) from e


def build_iso_data(tab: Path) -> tuple[dict, dict, dict]:
    """Read SIL's iso-639-3.tab and return three dicts.

    Returns:
        (iso1, iso2, iso3)
    """
    iso1: dict = {}
    iso2: dict = {}
    iso3: dict = {}

    try:
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
    except OSError as e:
        raise OperationalError(
            f"Could not read {tab}: {e}",
            source="filesystem",
            kind="transport",
        ) from e
    except csv.Error as e:
        raise OperationalError(
            f"Could not parse {tab}: {e}",
            source="iso_639_3",
            kind="invalid_response",
        ) from e

    log.info(
        "ISO 639-3: %d, ISO 639-2: %d, ISO 639-1: %d",
        len(iso3), len(iso2), len(iso1),
    )
    return iso1, iso2, iso3


def main() -> int:
    data_root = get_data_dir()
    default_tab = data_root / "iso_639_3.tab"
    default_iso3 = data_root / "iso_639_3.json"
    default_iso2 = data_root / "iso_639_2.json"
    default_iso1 = data_root / "iso_639_1.json"

    parser = argparse.ArgumentParser(
        description=(
            "Build ISO 639-1/2/3 JSON files from SIL .tab."
        ),
    )
    parser.add_argument(
        "--tab", type=Path, default=default_tab,
        help=f"SIL .tab file (default: {default_tab})",
    )
    parser.add_argument(
        "--iso3", type=Path, default=default_iso3,
        help=f"ISO 639-3 JSON (default: {default_iso3})",
    )
    parser.add_argument(
        "--iso2", type=Path, default=default_iso2,
        help=f"ISO 639-2 JSON (default: {default_iso2})",
    )
    parser.add_argument(
        "--iso1", type=Path, default=default_iso1,
        help=f"ISO 639-1 JSON (default: {default_iso1})",
    )
    args = parser.parse_args()

    if not args.tab.exists():
        log.error("Source file missing: %s", args.tab)
        return 1

    log.info("Reading: %s", args.tab)
    try:
        iso1, iso2, iso3 = build_iso_data(args.tab)
    except OperationalError as exc:
        log.error("%s", exc)
        return 1

    try:
        _atomic_write_json(args.iso3, iso3)
        _atomic_write_json(args.iso2, iso2)
        _atomic_write_json(args.iso1, iso1)
    except OperationalError as exc:
        log.error("%s", exc)
        return 1

    log.info(
        "Saved: %s, %s, %s", args.iso3, args.iso2, args.iso1
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
