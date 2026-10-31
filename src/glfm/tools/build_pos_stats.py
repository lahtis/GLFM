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
# Computes POS statistics from raw Wiktextract data.
# Requires: data/raw-wiktextract-data.jsonl.gz (5-10 GB)
# Produces: data/pos_stats.json
#
# This module does NOT use the network — it reads a local .jsonl.gz file.
#

import argparse
import gzip
import json
import logging
import os
from collections import defaultdict
from pathlib import Path

from glfm.errors import DataError, OperationalError
from glfm.paths import get_data_dir

log = logging.getLogger(__name__)


def _get_lang_code(entry: dict) -> str | None:
    """
    Extract language code from a Wiktextract entry.

    Wiktextract uses `lang_code` for ISO 639 codes (e.g. "fi").
    Some versions may use `lang` for the language name (e.g. "Finnish"),
    which is NOT a valid code — so we only accept `lang_code`.
    """
    code = entry.get("lang_code")
    if isinstance(code, str) and code.strip():
        return code.strip().lower()
    return None


def _atomic_write_json(path: Path, data: dict) -> None:
    """Atomic JSON write with human-readable formatting."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
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


def build_pos_stats(input_path: Path, output_path: Path) -> dict:
    """
    Compute POS statistics from raw Wiktextract data.

    Returns:
        {"fi": {"noun": 12345, "verb": 6789, ...}, ...}
    """
    if not input_path.exists():
        raise OperationalError(
            f"Input missing: {input_path}. "
            f"Download the Wiktextract dump (~5-10 GB) and save it here.",
            source="wiktextract",
            kind="transport",
        )

    pos_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    processed = 0
    used = 0
    errors = 0

    log.info("Reading: %s", input_path)
    try:
        with gzip.open(input_path, "rt", encoding="utf-8") as f:
            for line in f:
                processed += 1
                if processed % 1_000_000 == 0:
                    log.info("  %s lines processed...", f"{processed:,}")

                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    errors += 1
                    continue

                if not isinstance(entry, dict):
                    errors += 1
                    continue

                lang = _get_lang_code(entry)
                pos = entry.get("pos")
                if lang and pos:
                    pos_counts[lang][pos] += 1
                    used += 1
    except OSError as e:
        raise OperationalError(
            f"Could not read {input_path}: {e}",
            source="wiktextract",
            kind="transport",
        ) from e
    except (EOFError, gzip.BadGzipFile) as e:
        raise DataError(
            f"Corrupt gzip in {input_path}: {e}",
            source="wiktextract",
        ) from e

    # defaultdict -> plain dict
    result = {
        lang: dict(counts)
        for lang, counts in pos_counts.items()
    }

    log.info(
        "Processed %s lines, %d errors",
        f"{processed:,}", errors,
    )
    log.info(
        "Used %s / %s lines (%.1f%%)",
        f"{used:,}", f"{processed:,}",
        (used / processed * 100) if processed else 0.0,
    )
    log.info("Languages: %d", len(result))

    _atomic_write_json(output_path, result)
    log.info("Written: %s", output_path)
    return result


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    data_root = get_data_dir()
    default_input = data_root / "raw-wiktextract-data.jsonl.gz"
    default_output = data_root / "pos_stats.json"

    parser = argparse.ArgumentParser(
        description="Compute POS statistics from a Wiktextract dump.",
    )
    parser.add_argument(
        "--input", type=Path, default=default_input,
        help=f"Input file (default: {default_input})",
    )
    parser.add_argument(
        "--output", type=Path, default=default_output,
        help=f"Output file (default: {default_output})",
    )
    args = parser.parse_args()

    try:
        build_pos_stats(args.input, args.output)
    except OperationalError as exc:
        log.error("Source error: %s", exc)
        if exc.retryable:
            log.error("Error is temporary — try again later.")
        return 1
    except DataError as exc:
        log.error("Data error: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
