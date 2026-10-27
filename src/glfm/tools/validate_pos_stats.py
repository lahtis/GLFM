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
import sys
from pathlib import Path

# Ensure src/ is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from glfm.paths import get_data_dir

log = logging.getLogger(__name__)

DEFAULT_INPUT = get_data_dir() / "unified_languages.json"
DEFAULT_ERRORS = get_data_dir() / "validation" / "pos_stats_errors.json"


def validate_pos_stats(data: dict) -> list[str]:
    errors: list[str] = []
    for lang_id, info in data.items():
        if not isinstance(info, dict):
            continue
        pos = info.get("pos_stats")
        if not pos or not isinstance(pos, dict):
            continue
        for tag, count in pos.items():
            if not isinstance(tag, str):
                errors.append(f"{lang_id}: POS tag is not a string ({type(tag).__name__})")
                continue
            if not isinstance(count, int) or isinstance(count, bool):
                errors.append(f"{lang_id}: POS '{tag}' is not an integer ({type(count).__name__})")
            elif count < 0:
                errors.append(f"{lang_id}: POS '{tag}' is negative ({count})")
    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Validate POS statistics in unified_languages.json.",
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

    errors = validate_pos_stats(data)

    if errors:
        args.errors.parent.mkdir(parents=True, exist_ok=True)
        with open(args.errors, "w", encoding="utf-8") as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
        print(f"POS stats validation FAILED, see {args.errors}")
        for e in errors[:10]:
            print("  ", e)
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
        return 1

    print("POS stats validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
