#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.0.7
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
# Computes POS statistics from raw Wiktextract data.
# Requires: data/raw-wiktextract-data.jsonl.gz (5-10 GB)
# Produces: data/pos_stats.json
#

import argparse
import gzip
import json
import logging
import os
from collections import defaultdict
from pathlib import Path

from glfm.paths import get_data_dir

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = get_data_dir()
DEFAULT_INPUT = DATA_ROOT / "raw-wiktextract-data.jsonl.gz"
DEFAULT_OUTPUT = DATA_ROOT / "pos_stats.json"


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


def build_pos_stats(input_path: Path, output_path: Path) -> dict:
    """
    Compute POS statistics from raw Wiktextract data.

    Returns:
        {"fi": {"noun": 12345, "verb": 6789, ...}, ...}
    """
    if not input_path.exists():
        raise FileNotFoundError(
            f"Input missing: {input_path}\n"
            f"Download the Wiktextract dump (~5-10 GB) and save it here."
        )

    pos_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    processed = 0
    used = 0
    errors = 0

    log.info("Reading: %s", input_path)
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

            lang = _get_lang_code(entry)
            pos = entry.get("pos")
            if lang and pos:
                pos_counts[lang][pos] += 1
                used += 1

    # defaultdict → plain dict
    result = {lang: dict(counts) for lang, counts in pos_counts.items()}

    log.info("Processed %s lines, %d errors", f"{processed:,}", errors)
    log.info("Used %s / %s lines (%.1f%%)",
             f"{used:,}", f"{processed:,}",
             (used / processed * 100) if processed else 0.0)
    log.info("Languages: %d", len(result))

    # Atomic write
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(output_path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(output_path)

    log.info("Written: %s", output_path)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Compute POS statistics from a Wiktextract dump.",
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_INPUT,
        help=f"Input file (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help=f"Output file (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    build_pos_stats(args.input, args.output)


if __name__ == "__main__":
    main()
