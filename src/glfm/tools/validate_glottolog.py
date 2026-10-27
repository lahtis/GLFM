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
DEFAULT_ERRORS = get_data_dir() / "validation" / "glottolog_errors.json"

VALID_MACROAREAS = {
    "Africa", "Eurasia", "Australia", "Papunesia",
    "North America", "South America", "Antarctica",
}


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
                errors.append(f"{lang_id}: latitude is not a number ({type(lat).__name__})")
            elif not (-90 <= lat <= 90):
                errors.append(f"{lang_id}: latitude out of range ({lat})")
        if lon is not None:
            if not isinstance(lon, (int, float)):
                errors.append(f"{lang_id}: longitude is not a number ({type(lon).__name__})")
            elif not (-180 <= lon <= 180):
                errors.append(f"{lang_id}: longitude out of range ({lon})")
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


def main():
    parser = argparse.ArgumentParser(
        description="Validate Glottolog metadata in unified_languages.json.",
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

    errors = validate_glottolog(data)

    if errors:
        args.errors.parent.mkdir(parents=True, exist_ok=True)
        with open(args.errors, "w", encoding="utf-8") as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
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
