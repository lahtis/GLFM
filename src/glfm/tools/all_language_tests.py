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
# Validate unified_languages.json: check written/script consistency,
# UNKNOWN sentinels, and BCP-47 values.
#
# Output:
#   - all_languages_list.json (compact list of all languages)
#   - validation_errors.json (list of errors)
#

import argparse
import json
import logging
import os
from collections import Counter
from pathlib import Path

from glfm.errors import OperationalError
from glfm.paths import get_data_dir

log = logging.getLogger(__name__)


def validate(unified: dict) -> tuple[list[dict], list[dict]]:
    """Return (all_langs_list, errors).

    Pure function - no file writes. Testable with pytest.
    """
    errors: list[dict] = []
    all_langs_list: list[dict] = []

    for lang_id, lang in unified.items():
        entry = {
            "id": lang_id,
            "bcp47": lang.get("bcp47", ""),
            "default_script": lang.get("default_script", ""),
            "default_region": lang.get("default_region", ""),
            "written": bool(lang.get("written", False)),
            "written_scripts": lang.get("written_scripts", []),
            "uralicNLP": bool(lang.get("uralicNLP", False)),
        }
        all_langs_list.append(entry)

        ds = entry["default_script"]
        ws = entry["written_scripts"]
        bcp = entry["bcp47"]
        written = entry["written"]

        # --- Test 1: written=True requires a script ---
        # (empty script is OK for non-written languages)
        if written and not ds:
            errors.append({
                "id": lang_id,
                "type": "written_but_no_script",
                "value": ds,
            })

        # --- Test 1b: UNKNOWN is always an error (sentinel, not a value) ---
        if ds and ds.upper() == "UNKNOWN":
            errors.append({
                "id": lang_id,
                "type": "script_is_unknown_sentinel",
                "value": ds,
            })

        # --- Test 2: conflict between written flag and script list ---
        # (the earlier "default_script in written_scripts" check was
        #  circular because written_scripts is built from default_script)
        if written and not ws:
            errors.append({
                "id": lang_id,
                "type": "written_but_empty_scripts",
                "value": ws,
            })
        if not written and ws:
            errors.append({
                "id": lang_id,
                "type": "not_written_but_has_scripts",
                "value": ws,
            })

        # --- Test 3: written_scripts must not contain UNKNOWN ---
        for s in ws:
            if s.upper() == "UNKNOWN":
                errors.append({
                    "id": lang_id,
                    "type": "written_scripts_contains_unknown",
                    "value": ws,
                })
                break

        # --- Test 4: BCP47 must not contain -UNKNOWN or -001 ---
        if "-UNKNOWN" in bcp or "-001" in bcp:
            errors.append({
                "id": lang_id,
                "type": "bcp47_invalid_value",
                "value": bcp,
            })

        # --- Test 5: default_region 001 must not appear in BCP47 ---
        # (build_bcp47 already filters this, but just in case)
        region = entry["default_region"]
        if region == "001" and "-001" in bcp:
            errors.append({
                "id": lang_id,
                "type": "region_001_in_bcp47",
                "value": bcp,
            })

    return all_langs_list, errors


def save_json(path: Path, data) -> None:
    """Atomic JSON write with human-readable formatting."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(
                data, f,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)
    except OSError as e:
        raise OperationalError(
            f"Could not write {path}: {e}",
            source="filesystem",
            kind="transport",
        ) from e


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    data_dir = get_data_dir()
    default_input = data_dir / "unified" / "unified_languages.json"
    default_errors = data_dir / "unified" / "validation_errors.json"
    default_list = data_dir / "unified" / "all_languages_list.json"

    parser = argparse.ArgumentParser(
        description="Validate unified_languages.json",
    )
    parser.add_argument("--input", type=Path, default=default_input)
    parser.add_argument("--errors", type=Path, default=default_errors)
    parser.add_argument("--list", type=Path, default=default_list)
    args = parser.parse_args()

    if not args.input.exists():
        log.error("Input missing: %s", args.input)
        log.error("Run first: python3 -m glfm.build_unified")
        return 1

    log.info("Reading: %s", args.input)
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            unified = json.load(f)
    except json.JSONDecodeError as e:
        log.error("Invalid JSON in %s: %s", args.input, e)
        return 1
    except OSError as e:
        log.error("Could not read %s: %s", args.input, e)
        return 1

    all_langs, errors = validate(unified)

    try:
        save_json(args.list, all_langs)
        save_json(args.errors, errors)
    except OperationalError as e:
        log.error("%s", e)
        return 1

    # Summary
    print(f"\nValidation complete: {len(unified)} languages checked")
    print(f"Errors: {len(errors)}")
    print(f"Language list: {args.list}")
    print(f"Error list: {args.errors}")

    if errors:
        counts = Counter(e["type"] for e in errors)
        print("\nError types:")
        for vtype, n in counts.most_common():
            print(f"  {vtype}: {n}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
