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
# Compares JSON and Pickle packaging with stdlib dependencies only.
# This does NOT replace build_consumer_dataset.py — it is a
# comparison tool only.
#

import argparse
import gzip
import json
import logging
import os
import pickle
from pathlib import Path
from typing import Callable

from glfm.errors import DataError, OperationalError
from glfm.paths import get_data_dir

log = logging.getLogger(__name__)


def _atomic_write(path: Path, write_fn: Callable[[Path], None]) -> None:
    """Atomic write: tmp + replace."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        write_fn(tmp)
        tmp.replace(path)
    except OSError as e:
        raise OperationalError(
            f"Could not write {path}: {e}",
            source="filesystem",
            kind="transport",
        ) from e


def compress_variants(input_json: Path, output_dir: Path) -> dict:
    """Compress a JSON file two ways:
      - gzip + JSON  (.json.gz)
      - gzip + pickle (.pkl.gz)

    Returns a dict with file sizes in bytes.
    """
    if not input_json.exists():
        raise OperationalError(
            f"Input missing: {input_json}",
            source="filesystem",
            kind="transport",
        )

    log.info("Reading: %s", input_json)
    try:
        with open(input_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise DataError(
            f"Invalid JSON in {input_json}: {e}",
            source="unified_languages.json",
        ) from e
    except OSError as e:
        raise OperationalError(
            f"Could not read {input_json}: {e}",
            source="filesystem",
            kind="transport",
        ) from e

    out_json_gz = output_dir / (input_json.stem + ".json.gz")
    out_pkl_gz = output_dir / (input_json.stem + ".pkl.gz")

    # 1. Gzip + JSON
    def _write_json_gz(p: Path) -> None:
        with gzip.open(
            p, "wt", encoding="utf-8", compresslevel=9
        ) as gz:
            json.dump(
                data, gz,
                ensure_ascii=False,
                separators=(",", ":"),
            )

    _atomic_write(out_json_gz, _write_json_gz)

    # 2. Gzip + Pickle
    def _write_pkl_gz(p: Path) -> None:
        with gzip.open(p, "wb", compresslevel=9) as gz:
            pickle.dump(data, gz, protocol=pickle.HIGHEST_PROTOCOL)

    _atomic_write(out_pkl_gz, _write_pkl_gz)

    result = {
        "input": input_json.stat().st_size,
        "json_gz": out_json_gz.stat().st_size,
        "pkl_gz": out_pkl_gz.stat().st_size,
        "json_gz_path": out_json_gz,
        "pkl_gz_path": out_pkl_gz,
    }
    return result


def main() -> int:
    data_dir = get_data_dir()
    default_input = data_dir / "unified" / "languages_top20.json"

    parser = argparse.ArgumentParser(
        description="Compare gzip+JSON and gzip+Pickle packaging.",
    )
    parser.add_argument(
        "--input", type=Path, default=default_input,
        help=f"Input file (default: {default_input})",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=default_input.parent,
        help="Output directory (default: input's parent)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        r = compress_variants(args.input, args.output_dir)
    except OperationalError as exc:
        log.error("Source error: %s", exc)
        if exc.retryable:
            log.error("Error is temporary — try again later.")
        return 1
    except DataError as exc:
        log.error("Data error: %s", exc)
        return 1

    in_mb = r["input"] / (1024 * 1024)
    json_mb = r["json_gz"] / (1024 * 1024)
    pkl_mb = r["pkl_gz"] / (1024 * 1024)

    print()
    print("--- STDLIB (0 DEPENDENCY) COMPRESSION RESULTS ---")
    print(f"Original JSON:                {in_mb:8.2f} MB")
    print(
        f"Gzip JSON (.json.gz):         "
        f"{json_mb:8.2f} MB ({json_mb*1024:.0f} KB)"
    )
    print(
        f"Gzip Pickle (.pkl.gz):        "
        f"{pkl_mb:8.2f} MB ({pkl_mb*1024:.0f} KB)"
    )
    if in_mb > 0:
        print(
            f"\nSize saving .json.gz:         "
            f"{(1 - json_mb/in_mb) * 100:.1f} %"
        )
        print(
            f"Size saving .pkl.gz:          "
            f"{(1 - pkl_mb/in_mb) * 100:.1f} %"
        )
    print()
    print("Files:")
    print(f"  {r['json_gz_path']}")
    print(f"  {r['pkl_gz_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
