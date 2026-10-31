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
import gzip
import json
import logging
import os
from collections import Counter
from pathlib import Path

from glfm.errors import DataError, OperationalError
from glfm.paths import get_data_dir

log = logging.getLogger(__name__)

DEFAULT_TOP_K = 20

# Neighbor distance key order: from most precise to coarsest.
# If distance_6 is missing (e.g. old database), fall back to distance.
DISTANCE_KEYS = ("distance_6", "distance")


def is_living_written_language(lang_data: dict) -> bool:
    if not lang_data.get("written", False):
        return False
    ltype = lang_data.get("language_type", "")
    if ltype:
        return ltype == "L"
    return True


def _neighbor_distance(n: dict, default: float = 1.0) -> float:
    for key in DISTANCE_KEYS:
        if key in n and n[key] is not None:
            return n[key]
    return default


def filter_neighbors(
    lang_code: str,
    lang_data: dict,
    top_k: int,
    living_cache: dict,
) -> list[dict]:
    """Return up to top_k neighbors that are living written languages."""
    raw_neighbors = lang_data.get("nearest_languages", [])
    clean = []
    for n in raw_neighbors:
        target = n.get("lang")
        if not target or target == lang_code:
            continue
        if not living_cache.get(target, False):
            continue
        # Copy all fields (including distance and distance_6) so
        # precision is preserved at the consumer level.
        clean.append(dict(n))
        if len(clean) >= top_k:
            break
    return clean


def _atomic_write_json(path: Path, data: dict) -> None:
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


def _atomic_write_gzip(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            json.dump(
                data, f, ensure_ascii=False, separators=(",", ":")
            )
        tmp.replace(path)
    except OSError as e:
        raise OperationalError(
            f"Could not write {path}: {e}",
            source="filesystem",
            kind="transport",
        ) from e


def build_consumer_dataset(
    input_path: Path,
    output_json: Path,
    output_gz: Path,
    top_k: int = DEFAULT_TOP_K,
) -> None:
    if not input_path.exists():
        raise OperationalError(
            f"Input missing: {input_path}. "
            f"Run first: python3 -m glfm.build_unified",
            source="filesystem",
            kind="transport",
        )

    log.info("Reading: %s", input_path)
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            full_data = json.load(f)
    except json.JSONDecodeError as e:
        raise DataError(
            f"Invalid JSON in {input_path}: {e}",
            source="unified_languages.json",
        ) from e
    except OSError as e:
        raise OperationalError(
            f"Could not read {input_path}: {e}",
            source="filesystem",
            kind="transport",
        ) from e

    if not isinstance(full_data, dict):
        raise DataError(
            f"Expected a JSON object in {input_path}, "
            f"got {type(full_data).__name__}",
            source="unified_languages.json",
        )

    living_cache = {
        code: is_living_written_language(data)
        for code, data in full_data.items()
    }
    living_count = sum(1 for v in living_cache.values() if v)
    log.info(
        "Living written languages: %d/%d",
        living_count, len(full_data),
    )

    limited: dict = {}
    skip_reasons = Counter()
    notes = Counter()
    missing_family = 0

    for code, data in full_data.items():
        if not living_cache[code]:
            skip_reasons["not_living_written"] += 1
            continue

        entry = dict(data)
        entry["nearest_languages"] = filter_neighbors(
            code, data, top_k, living_cache
        )
        limited[code] = entry

        if not entry.get("family"):
            missing_family += 1

        n_neighbors = len(entry["nearest_languages"])
        if n_neighbors < top_k:
            notes[f"few_neighbors_{n_neighbors}"] += 1

    _atomic_write_json(output_json, limited)
    _atomic_write_gzip(output_gz, limited)

    in_size = input_path.stat().st_size / (1024 * 1024)
    out_size = output_json.stat().st_size / (1024 * 1024)
    gz_size = output_gz.stat().st_size / 1024

    print("\nDone!")
    print(
        f"  Input:        {len(full_data)} languages "
        f"({in_size:.2f} MB)"
    )
    print(
        f"  Output:       {len(limited)} languages "
        f"({out_size:.2f} MB)"
    )
    print(f"  Gzip:         {gz_size:.1f} kB")
    print(f"  Top-K:        {top_k} neighbors per language")
    print(f"  JSON:         {output_json}")
    print(f"  Gzip:         {output_gz}")

    if missing_family:
        print(
            f"\n  Note: {missing_family} languages have no family field"
        )

    if skip_reasons:
        print("\nFilter reasons:")
        for reason, count in skip_reasons.most_common(10):
            print(f"  {reason}: {count}")

    if notes:
        print("\nNotes:")
        for note, count in notes.most_common(10):
            print(f"  {note}: {count}")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    data_dir = get_data_dir()
    default_input = data_dir / "unified_languages.json"

    parser = argparse.ArgumentParser(
        description="Build consumer dataset from unified data.",
    )
    parser.add_argument(
        "-k", "--top-k", type=int, default=DEFAULT_TOP_K,
    )
    parser.add_argument(
        "-i", "--input", type=Path, default=default_input,
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
    )
    args = parser.parse_args()

    output_json = args.output or (
        data_dir / f"languages_top{args.top_k}.json"
    )
    output_gz = output_json.with_suffix(output_json.suffix + ".gz")

    try:
        build_consumer_dataset(
            input_path=args.input,
            output_json=output_json,
            output_gz=output_gz,
            top_k=args.top_k,
        )
    except OperationalError as exc:
        log.error("Source error: %s", exc)
        if exc.retryable:
            log.error("Error is temporary - try again later.")
        return 1
    except DataError as exc:
        log.error("Data error: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
