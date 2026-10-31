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
# Parse the ISO 639-2 source file (iso-639-2.txt) to JSON.
#

import argparse
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


def parse_iso_639_2(src: Path) -> dict:
    """Parse the ISO 639-2 source file.

    Line format: bcode|tcode|iso1|en_name|fr_name
    Returns a dict keyed by 3-letter code (T if present, otherwise B).
    """
    result: dict = {}
    skipped = 0

    try:
        with open(src, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split("|")
                if len(parts) < 5:
                    log.debug(
                        "Skipping line %d: too few fields", lineno
                    )
                    skipped += 1
                    continue

                bcode, tcode, iso1, en_name, _fr_name = [
                    p.strip() for p in parts[:5]
                ]

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
    except OSError as e:
        raise OperationalError(
            f"Could not read {src}: {e}",
            source="filesystem",
            kind="transport",
        ) from e

    log.info(
        "Parsed %d codes, skipped %d lines", len(result), skipped
    )
    return result


def main() -> int:
    data_root = get_data_dir()
    default_src = data_root / "iso-639-2.txt"
    default_out = data_root / "iso_639_2.json"

    parser = argparse.ArgumentParser(
        description="Parse the ISO 639-2 source file to JSON.",
    )
    parser.add_argument(
        "--input", type=Path, default=default_src,
        help=f"Source file (default: {default_src})",
    )
    parser.add_argument(
        "--output", type=Path, default=default_out,
        help=f"Output file (default: {default_out})",
    )
    args = parser.parse_args()

    if not args.input.exists():
        log.error("Source file missing: %s", args.input)
        return 1

    log.info("Reading: %s", args.input)
    try:
        result = parse_iso_639_2(args.input)
    except OperationalError as exc:
        log.error("%s", exc)
        return 1

    try:
        _atomic_write_json(args.output, result)
    except OperationalError as exc:
        log.error("%s", exc)
        return 1

    log.info(
        "Saved: %s (%d codes)", args.output, len(result)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
