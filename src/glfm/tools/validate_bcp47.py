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

BCP47_PATTERN = re.compile(
    r"^[a-z]{2,3}(-[A-Z][a-z]{3})?(-([A-Z]{2}|\d{3}))?$"
)


def validate_bcp47(data: dict) -> list[str]:
    errors: list[str] = []
    for lang_id, info in data.items():
        if not isinstance(info, dict):
            continue
        tag = info.get("bcp47")
        if not tag:
            continue
        if not isinstance(tag, str):
            errors.append(f"{lang_id}: bcp47 is not a string ({type(tag).__name__})")
            continue
        if not BCP47_PATTERN.match(tag):
            errors.append(f"{lang_id}: invalid bcp47 '{tag}'")
        if "-UNKNOWN" in tag:
            errors.append(f"{lang_id}: bcp47 contains UNKNOWN: '{tag}'")
        if "-001" in tag:
            errors.append(f"{lang_id}: bcp47 contains 001: '{tag}'")
    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Validate BCP-47 tags in unified_languages.json.",
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
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

    errors = validate_bcp47(data)

    if errors:
        print("BCP-47 validation FAILED")
        for e in errors:
            print("  ", e)
        return 1

    print("BCP-47 validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
