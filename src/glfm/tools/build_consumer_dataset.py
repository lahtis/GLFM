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
import gzip
import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path

# Ensure src/ is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from glfm.paths import get_data_dir

log = logging.getLogger(__name__)

OUTPUT_ROOT = get_data_dir()
DEFAULT_TOP_K = 20
DEFAULT_INPUT = OUTPUT_ROOT / "unified_languages.json"


def is_living_written_language(lang_data: dict) -> bool:
    if not lang_data.get("written", False):
        return False
    ltype = lang_data.get("language_type", "")
    if ltype:
        return ltype == "L"
    return True


def filter_neighbors(lang_code, lang_data, full_data, top_k, living_cache):
    raw_neighbors = lang_data.get("nearest_languages", [])
    clean = []
    for n in raw_neighbors:
        target = n.get("lang")
        dist = n.get("distance", 1.0)
        if not target or target == lang_code:
            continue
        if not living_cache.get(target, False):
            continue
        clean.append({"lang": target, "distance": dist})
        if len(clean) >= top_k:
            break
    return clean


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def _atomic_write_gzip(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    tmp.replace(path)


def build_consumer_dataset(input_path, output_json, output_gz, top_k=DEFAULT_TOP_K):
    if not input_path.exists():
        raise SystemExit(
            f"Input missing: {input_path}\n"
            f"Run first: python3 -m glfm.build_unified"
        )

    log.info("Reading: %s", input_path)
    with open(input_path, "r", encoding="utf-8") as f:
        full_data = json.load(f)

    living_cache = {
        code: is_living_written_language(data)
        for code, data in full_data.items()
    }
    living_count = sum(1 for v in living_cache.values() if v)
    log.info("Living written languages: %d/%d", living_count, len(full_data))

    limited: dict = {}
    skip_reasons = Counter()
    missing_family = 0

    for code, data in full_data.items():
        if not living_cache[code]:
            skip_reasons["not_living_written"] += 1
            continue

        entry = dict(data)
        entry["nearest_languages"] = filter_neighbors(
            code, data, full_data, top_k, living_cache
        )
        limited[code] = entry

        if not entry.get("family"):
            missing_family += 1

        n_neighbors = len(entry["nearest_languages"])
        if n_neighbors < top_k:
            skip_reasons[f"few_neighbors_{n_neighbors}"] += 1

    _atomic_write_json(output_json, limited)
    _atomic_write_gzip(output_gz, limited)

    in_size = input_path.stat().st_size / (1024 * 1024)
    out_size = output_json.stat().st_size / (1024 * 1024)
    gz_size = output_gz.stat().st_size / 1024

    print(f"\nDone!")
    print(f"  Input:        {len(full_data)} languages ({in_size:.2f} MB)")
    print(f"  Output:       {len(limited)} languages ({out_size:.2f} MB)")
    print(f"  Gzip:         {gz_size:.1f} kB")
    print(f"  Top-K:        {top_k} neighbors per language")
    print(f"  JSON:         {output_json}")
    print(f"  Gzip:         {output_gz}")

    if missing_family:
        print(f"\n  Note: {missing_family} languages have no family field")

    if skip_reasons:
        print(f"\nFilter reasons:")
        for reason, count in skip_reasons.most_common(10):
            print(f"  {reason}: {count}")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Build consumer dataset from unified data.",
    )
    parser.add_argument("-k", "--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=None)
    args = parser.parse_args()

    output_json = args.output or (OUTPUT_ROOT / f"languages_top{args.top_k}.json")
    output_gz = output_json.with_suffix(output_json.suffix + ".gz")

    build_consumer_dataset(
        input_path=args.input,
        output_json=output_json,
        output_gz=output_gz,
        top_k=args.top_k,
    )


if __name__ == "__main__":
    main()
