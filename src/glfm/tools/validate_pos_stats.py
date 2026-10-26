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
import sys
from pathlib import Path

from glfm.paths import get_data_dir, get_output_dir

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = get_output_dir() / "unified" / "unified_languages.json"
DEFAULT_ERRORS = get_output_dir() / "validation" / "pos_stats_errors.json"


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
                errors.append(f"{lang_id}: POS tag ei ole merkkijono ({type(tag).__name__})")
                continue
            if not isinstance(count, int) or isinstance(count, bool):
                errors.append(f"{lang_id}: POS '{tag}' ei ole kokonaisluku ({type(count).__name__})")
            elif count < 0:
                errors.append(f"{lang_id}: POS '{tag}' negatiivinen ({count})")
    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Validoi POS-tilastot unified_languages.json:sta.",
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--errors", type=Path, default=DEFAULT_ERRORS)
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

    errors = validate_pos_stats(data)

    if errors:
        args.errors.parent.mkdir(parents=True, exist_ok=True)
        with open(args.errors, "w", encoding="utf-8") as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
        print(f"POS stats validation FAILED, see {args.errors}")
        for e in errors[:10]:
            print("  ", e)
        if len(errors) > 10:
            print(f"  ... ja {len(errors) - 10} muuta")
        return 1

    print("POS stats validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
