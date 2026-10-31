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

import argparse
import json
import logging
import os
from pathlib import Path

from glfm.errors import OperationalError
from glfm.paths import get_data_dir

log = logging.getLogger(__name__)

# SIL Language_Type values that count as "dead":
#   E = Extinct
#   A = Ancient
#   H = Historical
EXTINCT_TYPES = ("E", "A", "H")


def _atomic_write_json(path: Path, data: dict) -> None:
    """Atomic JSON write."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)
    except OSError as e:
        raise OperationalError(
            f"Could not write {path}: {e}",
            source="filesystem",
            kind="transport",
        ) from e


def generate_extinct_json(iso_tab: Path, output_json: Path) -> None:
    """Read ISO 639-3 .tab and generate a small JSON of dead languages.

    Preserves previous manual additions (e.g. 'lat') if the output file
    already exists.
    """
    extinct_codes: set[str] = set()

    # 1. Collect E/A/H codes from the ISO 639-3 table
    if iso_tab.exists():
        log.info("Reading ISO table: %s", iso_tab)
        try:
            with open(iso_tab, "r", encoding="utf-8") as f:
                f.readline()  # skip header
                for line in f:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) >= 6:
                        lang_id = parts[0].strip()
                        lang_type = parts[5].strip()
                        if lang_id and lang_type in EXTINCT_TYPES:
                            extinct_codes.add(lang_id)
        except OSError as e:
            raise OperationalError(
                f"Could not read {iso_tab}: {e}",
                source="iso_639_3",
                kind="transport",
            ) from e
        log.info(
            "Found %d codes in ISO table", len(extinct_codes)
        )
    else:
        log.warning("File not found: %s", iso_tab)

    # 2. Preserve previous manual additions
    if output_json.exists():
        try:
            with open(output_json, "r", encoding="utf-8") as f:
                old_data = json.load(f)
            old_codes = old_data.get("codes", [])
            if isinstance(old_codes, list):
                extinct_codes.update(old_codes)
                log.info(
                    "Preserved %d previous manual codes",
                    len(old_codes),
                )
        except (json.JSONDecodeError, OSError, TypeError) as e:
            log.warning("Could not read %s: %s", output_json, e)

    sorted_codes = sorted(extinct_codes)

    data_to_save = {
        "description": (
            "Pre-processed list of ISO 639-3 dead/historical languages "
            "and manual additions."
        ),
        "count": len(sorted_codes),
        "codes": sorted_codes,
    }

    _atomic_write_json(output_json, data_to_save)

    log.info(
        "Done. Saved %d dead language codes: %s",
        len(sorted_codes), output_json,
    )


def main() -> int:
    data_root = get_data_dir()
    default_iso_tab = data_root / "iso_639_3.tab"
    default_output = data_root / "extinct_languages.json"

    parser = argparse.ArgumentParser(
        description=(
            "Generate a JSON list of dead ISO 639-3 languages."
        ),
    )
    parser.add_argument(
        "--input", type=Path, default=default_iso_tab,
        help=f"ISO 639-3 .tab file (default: {default_iso_tab})",
    )
    parser.add_argument(
        "--output", type=Path, default=default_output,
        help=f"Output JSON (default: {default_output})",
    )
    args = parser.parse_args()

    try:
        generate_extinct_json(args.input, args.output)
    except OperationalError as exc:
        log.error("%s", exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
