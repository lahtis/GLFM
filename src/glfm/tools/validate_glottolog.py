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

VALID_MACROAREAS = {
    "Africa", "Eurasia", "Australia", "Papunesia",
    "North America", "South America", "Antarctica",
}


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


def validate_glottolog(data: dict) -> list[str]:
    errors: list[str] = []
    for lang_id, info in data.items():
        if not isinstance(info, dict):
            continue
        gl = info.get("glottolog")
        if not gl or not isinstance(gl, dict):
            continue
        macro = gl.get("macroarea")
        if macro and macro not in VALID_MACROAREAS:
            errors.append(f"{lang_id}: invalid macroarea '{macro}'")
        lat = gl.get("latitude")
        lon = gl.get("longitude")
        if lat is not None:
            if not isinstance(lat, (int, float)):
                errors.append(
                    f"{lang_id}: latitude is not a number "
                    f"({type(lat).__name__})"
                )
            elif not (-90 <= lat <= 90):
                errors.append(
                    f"{lang_id}: latitude out of range ({lat})"
                )
        if lon is not None:
            if not isinstance(lon, (int, float)):
                errors.append(
                    f"{lang_id}: longitude is not a number "
                    f"({type(lon).__name__})"
                )
            elif not (-180 <= lon <= 180):
                errors.append(
                    f"{lang_id}: longitude out of range ({lon})"
                )
        lineage = gl.get("lineage")
        if lineage is not None and not isinstance(lineage, list):
            errors.append(f"{lang_id}: lineage is not a list")
        family = gl.get("family")
        if family is not None and not isinstance(family, str):
            errors.append(f"{lang_id}: family is not a string")
        gc = gl.get("glottocode")
        if gc is not None and not isinstance(gc, str):
            errors.append(f"{lang_id}: glottocode is not a string")
    return errors


def main() -> int:
    data_root = get_data_dir()
    default_input = data_root / "unified_languages.json"
    default_errors = data_root / "validation" / "glottolog_errors.json"

    parser = argparse.ArgumentParser(
        description=(
            "Validate Glottolog metadata in unified_languages.json."
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

    errors = validate_glottolog(data)

    if errors:
        try:
            _atomic_write_json(args.errors, errors)
        except OperationalError as exc:
            log.error("%s", exc)
            return 1
        print(f"Glottolog validation FAILED, see {args.errors}")
        for e in errors[:10]:
            print("  ", e)
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
        return 1

    print("Glottolog validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
