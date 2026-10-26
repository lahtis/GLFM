#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM / Self-Healing Localization (SHL)
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.0.2
#
# Licensed under the MIT License.
#
# Vertailee JSON- ja Pickle-pakkausta stdlib-riippuvuuksilla.
# EI korvaa build_consumer_dataset.py:tä – tämä on vain vertailutyökalu.
#

import argparse
import gzip
import json
import logging
import os
import pickle
from pathlib import Path

from glfm.paths import get_data_dir, get_output_dir

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = get_output_dir() / "unified" / "languages_top20.json"


def _atomic_write(path: Path, write_fn) -> None:
    """Atominen kirjoitus: tmp + replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    write_fn(tmp)
    tmp.replace(path)


def compress_variants(input_json: Path, output_dir: Path) -> dict:
    """
    Pakkaa annetun JSON-tiedoston kahdella tavalla:
      - gzip + JSON  (.json.gz)
      - gzip + pickle (.pkl.gz)

    Palauttaa dictin, jossa on tiedostokoot tavuina.
    """
    if not input_json.exists():
        raise FileNotFoundError(f"Syöte puuttuu: {input_json}")

    log.info("Luetaan: %s", input_json)
    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    out_json_gz = output_dir / (input_json.stem + ".json.gz")
    out_pkl_gz = output_dir / (input_json.stem + ".pkl.gz")

    # 1. Gzip + JSON
    def _write_json_gz(p: Path) -> None:
        with gzip.open(p, "wt", encoding="utf-8", compresslevel=9) as gz:
            json.dump(data, gz, ensure_ascii=False, separators=(",", ":"))

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


def main():
    parser = argparse.ArgumentParser(
        description="Vertaile gzip+JSON ja gzip+Pickle -pakkausta.",
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_INPUT,
        help=f"Syöte (oletus: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_INPUT.parent,
        help="Tulosteiden hakemisto (oletus: syötteen hakemisto)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        r = compress_variants(args.input, args.output_dir)
    except FileNotFoundError as e:
        log.error("%s", e)
        return 1

    in_mb = r["input"] / (1024 * 1024)
    json_mb = r["json_gz"] / (1024 * 1024)
    pkl_mb = r["pkl_gz"] / (1024 * 1024)

    print()
    print("--- STDLIB (0 DEPENDENCY) COMPRESSION RESULTS ---")
    print(f"Alkuperäinen JSON:            {in_mb:8.2f} MB")
    print(f"Gzip JSON (.json.gz):         {json_mb:8.2f} MB ({json_mb*1024:.0f} KB)")
    print(f"Gzip Pickle (.pkl.gz):        {pkl_mb:8.2f} MB ({pkl_mb*1024:.0f} KB)")
    if in_mb > 0:
        print(f"\nKoon säästö .json.gz:        {(1 - json_mb/in_mb) * 100:.1f} %")
        print(f"Koon säästö .pkl.gz:         {(1 - pkl_mb/in_mb) * 100:.1f} %")
    print()
    print(f"Tiedostot:")
    print(f"  {r['json_gz_path']}")
    print(f"  {r['pkl_gz_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
