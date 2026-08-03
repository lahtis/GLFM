#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Global Language Family Mapper (GLFM)
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.0.1
#
# https://codeberg.org/lahtis/GLFM
#
# Licensed under the MIT License.
# You may obtain a copy of the License at:
# https://opensource.org/licenses/MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

"""
tools/compute_nearest_languages.py

Attaches a `nearest_languages` field to written languages in
GLFM's unified_languages.json, ranking other written languages by
lang2vec / URIEL genetic distance.

Usage:
    python3 tools/compute_nearest_languages.py
    python3 tools/compute_nearest_languages.py --input other.json --output other_out.json
    python3 tools/compute_nearest_languages.py --no-backup
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import lang2vec.lang2vec as l2v
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("compute_nearest_languages")

DEFAULT_FILE = Path("output/unified/unified_languages.json")
BACKUP_DIR = Path("output/unified/backups")

DISTANCE_TYPE = "fam"
DISTANCE_SOURCE = "lang2vec / URIEL"
DISTANCE_BASES = ["WALS", "SSWL", "PHOIBLE", "Ethnologue", "Glottolog"]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def make_backup(path: Path) -> Optional[Path]:
    """Copy the existing file to a timestamped backup before overwriting it."""
    if not path.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUP_DIR / f"{path.stem}.{stamp}{path.suffix}"
    shutil.copy2(path, backup_path)
    log.info("Backup written to %s", backup_path)
    return backup_path


def is_written_language(item: dict) -> bool:
    """
    Kieli lasketaan kirjoitetuksi kieleksi, jos:
      1. 'written' on True, TAI
      2. 'written_scripts' sisältää vähintään yhden merkistön (esim. ["Latn"])
    """
    if not isinstance(item, dict):
        return False

    if item.get("written") is True:
        return True

    scripts = item.get("written_scripts")
    if isinstance(scripts, list) and len(scripts) > 0:
        return True

    return False


def get_lang_code(lang_id: str, item: dict) -> Optional[str]:
    """Hakee ISO 639-3 koodin ja varmistaa että se on 3-kirjaiminen validi merkkijono."""
    code = item.get("iso639_3") or item.get("code") or lang_id
    code_str = str(code).lower().strip() if code else ""

    if len(code_str) == 3 and code_str.isalpha():
        return code_str
    return None


def collect_written_codes(data: dict) -> Dict[str, str]:
    """Return {lang_id: lang_code} for written languages only."""
    langs: Dict[str, str] = {}
    for lang_id, item in data.items():
        if not is_written_language(item):
            continue
        code = get_lang_code(lang_id, item)
        if code:
            langs[lang_id] = code
    return langs


def compute_distance_matrix(codes: List[str]):
    """Laske etäisyysmatriisi lang2vec-featureista."""
    n = len(codes)
    matrix = np.zeros((n, n))
    
    log.info("Fetching '%s' features for %d languages...", DISTANCE_TYPE, n)
    
    # Hae kaikkien kielten featuret
    features = {}
    for code in codes:
        try:
            feat_dict = l2v.get_features([code], DISTANCE_TYPE)
            features[code] = feat_dict.get(code, None)
        except Exception as e:
            log.warning(f"Could not get features for {code}: {e}")
            features[code] = None
    
    # Laske etäisyydet (Hamming-etäisyys)
    log.info("Computing pairwise distances...")
    for i, code1 in enumerate(codes):
        for j, code2 in enumerate(codes):
            if i == j:
                matrix[i][j] = 0.0
                continue
            
            f1 = features.get(code1)
            f2 = features.get(code2)
            
            if f1 is None or f2 is None:
                matrix[i][j] = float('nan')
                continue
            
            if len(f1) != len(f2):
                matrix[i][j] = float('nan')
                continue
            
            # Laske eroavien featureiden osuus
            diff = sum(1 for a, b in zip(f1, f2) if a != b)
            matrix[i][j] = diff / len(f1) if len(f1) > 0 else 0.0
    
    return matrix


def build_nearest_map(data: dict) -> Dict[str, list]:
    langs = collect_written_codes(data)
    lang_ids = list(langs.keys())
    codes = [langs[lid] for lid in lang_ids]

    if not lang_ids:
        log.warning("No written languages with valid ISO 639-3 codes found!")
        return {}

    log.info("Computing '%s' distances for %d written languages...", DISTANCE_TYPE, len(lang_ids))

    try:
        matrix = compute_distance_matrix(codes)
    except Exception:
        log.exception(
            "Batched lang2vec distance call failed for %d languages.",
            len(lang_ids),
        )
        raise

    nearest_map: Dict[str, list] = {}
    missing_codes = set()

    for i, lang_id in enumerate(lang_ids):
        distances = []
        row = matrix[i]
        for j, other_id in enumerate(lang_ids):
            if i == j:
                continue
            d = row[j]
            if d is None or d != d:  # NaN-tarkistus
                missing_codes.add(codes[i])
                continue
            distances.append({"lang": other_id, "distance": round(float(d), 4)})

        distances.sort(key=lambda x: x["distance"])
        nearest_map[lang_id] = distances

    if missing_codes:
        log.warning(
            "%d language codes had no usable '%s' distance data in URIEL "
            "(their nearest_languages entries will be incomplete): %s",
            len(missing_codes), DISTANCE_TYPE, ", ".join(sorted(missing_codes)[:20]),
        )

    return nearest_map


def attach_metadata(data: dict) -> None:
    for lang_id, item in data.items():
        if not is_written_language(item):
            continue
        item["distance_source"] = DISTANCE_SOURCE
        item["distance_type"] = DISTANCE_TYPE
        item["distance_bases"] = DISTANCE_BASES


def run(input_path: Path, output_path: Path, do_backup: bool = True) -> None:
    data = load_json(input_path)
    nearest_map = build_nearest_map(data)

    for lang_id, nearest in nearest_map.items():
        if lang_id in data:
            data[lang_id]["nearest_languages"] = nearest

    attach_metadata(data)

    if output_path == input_path and do_backup:
        make_backup(input_path)

    save_json(output_path, data)
    log.info("Wrote nearest_languages for %d languages to %s", len(nearest_map), output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Attach nearest-language data to GLFM's unified_languages.json"
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_FILE)
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Defaults to overwriting --input (a backup is made first unless --no-backup is set).",
    )
    parser.add_argument("--no-backup", action="store_true", help="Skip backup before overwrite.")
    args = parser.parse_args()

    output_path = args.output or args.input
    run(args.input, output_path, do_backup=not args.no_backup)


if __name__ == "__main__":
    main()
