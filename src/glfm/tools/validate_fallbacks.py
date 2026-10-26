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
DEFAULT_ERRORS = get_output_dir() / "validation" / "fallback_errors.json"


def _detect_loop(start: str, data: dict, max_depth: int = 100) -> str | None:
    visited = set()
    current = start
    for _ in range(max_depth):
        if current in visited:
            return current
        visited.add(current)
        if current not in data:
            return None
        next_fb = data[current].get("fallback")
        if not next_fb or next_fb == current:
            return None
        current = next_fb
    return current


def validate_fallbacks(data: dict) -> list[str]:
    errors: list[str] = []
    for lang_id, info in data.items():
        if not isinstance(info, dict):
            continue
        fb = info.get("fallback")
        if not fb:
            errors.append(f"{lang_id}: missing fallback")
            continue
        if not isinstance(fb, str):
            errors.append(f"{lang_id}: fallback ei ole merkkijono ({type(fb).__name__})")
            continue
        if fb not in data:
            errors.append(f"{lang_id}: fallback '{fb}' does not exist")
            continue
        loop_node = _detect_loop(fb, data)
        if loop_node is not None:
            errors.append(f"{lang_id}: fallback loop detected ({loop_node})")
    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Validoi fallback-ketjut unified_languages.json:sta.",
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

    errors = validate_fallbacks(data)

    if errors:
        args.errors.parent.mkdir(parents=True, exist_ok=True)
        with open(args.errors, "w", encoding="utf-8") as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
        print(f"Fallback validation FAILED, see {args.errors}")
        for e in errors[:10]:
            print("  ", e)
        if len(errors) > 10:
            print(f"  ... ja {len(errors) - 10} muuta")
        return 1

    print("All fallback chains are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
