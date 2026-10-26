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
DEFAULT_ERRORS = get_output_dir() / "validation" / "glottolog_errors.json"

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
                errors.append(f"{lang_id}: latitude ei ole numero ({type(lat).__name__})")
            elif not (-90 <= lat <= 90):
                errors.append(f"{lang_id}: latitude out of range ({lat})")
        if lon is not None:
            if not isinstance(lon, (int, float)):
                errors.append(f"{lang_id}: longitude ei ole numero ({type(lon).__name__})")
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
        description="Validoi Glottolog-metadata unified_languages.json:sta.",
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

    errors = validate_glottolog(data)

    if errors:
        args.errors.parent.mkdir(parents=True, exist_ok=True)
        with open(args.errors, "w", encoding="utf-8") as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
        print(f"Glottolog validation FAILED, see {args.errors}")
        for e in errors[:10]:
            print("  ", e)
        if len(errors) > 10:
            print(f"  ... ja {len(errors) - 10} muuta")
        return 1

    print("Glottolog validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
