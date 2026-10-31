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
import sys
from pathlib import Path

from glfm.errors import OperationalError
from glfm.paths import get_data_dir

log = logging.getLogger(__name__)


def _atomic_write_json(path: Path, data) -> None:
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
                errors.append(
                    f"{lang_id}: POS tag is not a string "
                    f"({type(tag).__name__})"
                )
                continue
            if not isinstance(count, int) or isinstance(count, bool):
                errors.append(
                    f"{lang_id}: POS '{tag}' is not an integer "
                    f"({type(count).__name__})"
                )
            elif count < 0:
                errors.append(
                    f"{lang_id}: POS '{tag}' is negative ({count})"
                )
    return errors


def main() -> int:
    data_root = get_data_dir()
    default_input = data_root / "unified_languages.json"
    default_errors = (
        data_root / "validation" / "pos_stats_errors.json"
    )

    parser = argparse.ArgumentParser(
        description=(
            "Validate POS statistics in unified_languages.json."
        ),
    )
    parser.add_argument("--input", type=Path, default=default_input)
    parser.add_argument("--errors", type=Path, default=default_errors)
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

    errors = validate_pos_stats(data)

    if errors:
        try:
            _atomic_write_json(args.errors, errors)
        except OperationalError as exc:
            log.error("%s", exc)
            return 1
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
