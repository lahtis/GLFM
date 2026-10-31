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
import re
import sys
from pathlib import Path

from glfm.errors import DataError, OperationalError
from glfm.paths import get_data_dir

log = logging.getLogger(__name__)

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
            errors.append(
                f"{lang_id}: bcp47 is not a string "
                f"({type(tag).__name__})"
            )
            continue
        if not BCP47_PATTERN.match(tag):
            errors.append(f"{lang_id}: invalid bcp47 '{tag}'")
        if "-UNKNOWN" in tag:
            errors.append(
                f"{lang_id}: bcp47 contains UNKNOWN: '{tag}'"
            )
        if "-001" in tag:
            errors.append(f"{lang_id}: bcp47 contains 001: '{tag}'")
    return errors


def main() -> int:
    data_root = get_data_dir()
    default_input = data_root / "unified_languages.json"

    parser = argparse.ArgumentParser(
        description="Validate BCP-47 tags in unified_languages.json.",
    )
    parser.add_argument("--input", type=Path, default=default_input)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
        stream=sys.stdout,
    )

    if not args.input.exists():
        log.error("Input missing: %s", args.input)
        log.error("Run first: python3 -m glfm.build_unified")
        return 1

    log.info("Reading: %s", args.input)
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        log.error("Invalid JSON in %s: %s", args.input, e)
        return 1
    except OSError as e:
        log.error("Could not read %s: %s", args.input, e)
        return 1

    if not isinstance(data, dict):
        log.error(
            "Expected a JSON object, got %s", type(data).__name__
        )
        return 1

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
