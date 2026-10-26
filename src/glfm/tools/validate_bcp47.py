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

import argparse
import json
import logging
import re
import sys
from pathlib import Path

from glfm.paths import get_data_dir, get_output_dir

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = get_output_dir() / "unified" / "unified_languages.json"

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
            errors.append(f"{lang_id}: bcp47 ei ole merkkijono ({type(tag).__name__})")
            continue
        if not BCP47_PATTERN.match(tag):
            errors.append(f"{lang_id}: invalid bcp47 '{tag}'")
        if "-UNKNOWN" in tag:
            errors.append(f"{lang_id}: bcp47 sisältää UNKNOWN: '{tag}'")
        if "-001" in tag:
            errors.append(f"{lang_id}: bcp47 sisältää 001: '{tag}'")
    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Validoi BCP-47-tagit unified_languages.json:sta.",
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
        stream=sys.stdout,   # ← INFO stdoutiin
    )

    if not args.input.exists():
        raise SystemExit(
            f"Syöte puuttuu: {args.input}\n"
            f"Aja ensin: python3 build_unified.py"
        )

    log.info("Luetaan: %s", args.input)
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
