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
# Laskee POS-tilastot Wiktextractin raakadatasta.
# Vaatii: data/raw-wiktextract-data.jsonl.gz (5-10 Gt)
# Tuottaa: data/pos_stats.json
#

import argparse
import gzip
import json
import logging
import os
from collections import defaultdict
from pathlib import Path

from glfm.paths import get_data_dir, get_output_dir

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = get_data_dir()
DEFAULT_INPUT = DATA_ROOT / "raw-wiktextract-data.jsonl.gz"
DEFAULT_OUTPUT = DATA_ROOT / "pos_stats.json"


def build_pos_stats(input_path: Path, output_path: Path) -> dict:
    """
    Laskee POS-tilastot Wiktextractin raakadatasta.

    Palauttaa rakenteen:
        {"fi": {"noun": 12345, "verb": 6789, ...}, ...}
    """
    if not input_path.exists():
        raise FileNotFoundError(
            f"Syöte puuttuu: {input_path}\n"
            f"Lataa Wiktextract-dump (~5-10 Gt) ja tallenna se tähän."
        )

    pos_counts = defaultdict(lambda: defaultdict(int))
    processed = 0
    errors = 0

    log.info("Luetaan: %s", input_path)
    with gzip.open(input_path, "rt", encoding="utf-8") as f:
        for line in f:
            processed += 1
            if processed % 1_000_000 == 0:
                log.info("  %s riviä käsitelty...", f"{processed:,}")

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                errors += 1
                continue

            lang = entry.get("lang_code")
            pos = entry.get("pos")
            if lang and pos:
                pos_counts[lang][pos] += 1

    # defaultdict → tavallinen dict
    result = {lang: dict(counts) for lang, counts in pos_counts.items()}

    log.info("Käsitelty %s riviä, %d virhettä", f"{processed:,}", errors)
    log.info("Kieliä: %d", len(result))

    # Atominen kirjoitus
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(output_path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(output_path)

    log.info("Tallennettu: %s", output_path)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Laske POS-tilastot Wiktextract-dumpista.",
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_INPUT,
        help=f"Syöte (oletus: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help=f"Tuloste (oletus: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    build_pos_stats(args.input, args.output)


if __name__ == "__main__":
    main()
