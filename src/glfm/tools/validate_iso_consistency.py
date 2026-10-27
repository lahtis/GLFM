#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.0.5
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#

import argparse
import json
import logging
import re
import sys
from pathlib import Path

# Ensure src/ is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from glfm.paths import get_data_dir

log = logging.getLogger(__name__)

DEFAULT_INPUT = get_data_dir() / "unified_languages.json"
DEFAULT_ERRORS = get_data_dir() / "validation" / "iso_errors.json"

ISO1_PATTERN = re.compile(r"^[a-z]{2}$")
ISO23_PATTERN = re.compile(r"^[a-z]{3}$")


def validate_iso(data: dict) -> list[str]:
    errors: list[str] = []
    for lang_id, info in data.items():
        if not isinstance(info, dict):
            continue
        iso1 = info.get("iso639_1", "")
        iso2B = info.get("iso639_2B", "")
        iso2T = info.get("iso639_2T", "")
        iso3 = info.get("iso639_3", "")
        iso5 = info.get("iso639_5", "")

        if iso1 and not ISO1_PATTERN.match(iso1):
            errors.append(f"{lang_id}: invalid iso639_1 '{iso1}'")
        if iso3 and not ISO23_PATTERN.match(iso3):
            errors.append(f"{lang_id}: invalid iso639_3 '{iso3}'")
        if iso2B and not ISO23_PATTERN.match(iso2B):
            errors.append(f"{lang_id}: invalid iso639_2B '{iso2B}'")
        if iso2T and not ISO23_PATTERN.match(iso2T):
            errors.append(f"{lang_id}: invalid iso639_2T '{iso2T}'")
        if iso5 and iso3:
            errors.append(f"{lang_id}: has both iso639_3 and iso639_5")
        if iso5 and not ISO23_PATTERN.match(iso5):
            errors.append(f"{lang_id}: invalid iso639_5 '{iso5}'")
        if iso1 and not iso3:
            errors.append(f"{lang_id}: has iso639_1 but no iso639_3")
    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Validate ISO code consistency.",
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--errors", type=Path, default=DEFAULT_ERRORS)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
        stream=sys.stdout,
    )

    if not args.input.exists():
        raise SystemExit(
            f"Input missing: {args.input}\n"
            f"Run first: python3 -m glfm.build_unified"
        )

    log.info("Reading: %s", args.input)
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    errors = validate_iso(data)

    if errors:
        args.errors.parent.mkdir(parents=True, exist_ok=True)
        with open(args.errors, "w", encoding="utf-8") as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
        print(f"ISO validation FAILED, see {args.errors}")
        for e in errors[:10]:
            print("  ", e)
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
        return 1

    print("All ISO codes are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
