#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.0.4
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Varmista että src/ on sys.path:ssä
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

import lang2vec.lang2vec as l2v
import numpy as np

from glfm.paths import get_output_dir

log = logging.getLogger("compute_nearest_languages")

# --- Polut (glfm.paths:stä) ---
OUTPUT_ROOT = get_output_dir()
DEFAULT_FILE = OUTPUT_ROOT / "unified" / "unified_languages.json"
BACKUP_DIR = OUTPUT_ROOT / "unified" / "backups"
CHECKPOINT_PATH = OUTPUT_ROOT / "unified" / "nearest_languages.checkpoint.json"
CHECKPOINT_INTERVAL = 1000

MAX_NEIGHBORS = 100

DISTANCE_TYPE = "fam"
DISTANCE_SOURCE = "lang2vec / URIEL"
DISTANCE_BASES = ["WALS", "SSWL", "PHOIBLE", "Ethnologue", "Glottolog"]

try:
    from glfm._version import __version__ as GLFM_VERSION
except ImportError:
    GLFM_VERSION = "1.0.4"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    """Kirjoittaa sekä plain-JSON että gzip."""
    import gzip

    path.parent.mkdir(parents=True, exist_ok=True)

    # Plain JSON (debug)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

    # Gzip JSON (tuotanto)
    gz_path = path.with_suffix(path.suffix + ".gz")
    tmp_gz = gz_path.with_suffix(gz_path.suffix + ".tmp")
    with gzip.open(tmp_gz, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_gz, gz_path)

    log.info("Kirjoitettu: %s ja %s", path, gz_path)


def make_backup(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUP_DIR / f"{path.stem}.{stamp}{path.suffix}"
    shutil.copy2(path, backup_path)
    log.info("Backup written to %s", backup_path)
    return backup_path


def is_written_language(item: dict) -> bool:
    if not isinstance(item, dict):
        return False
    if item.get("written") is True:
        return True
    scripts = item.get("written_scripts")
    return isinstance(scripts, list) and len(scripts) > 0


def get_lang_code(lang_id: str, item: dict) -> Optional[str]:
    code = item.get("iso639_3") or item.get("code") or lang_id
    code_str = str(code).lower().strip() if code else ""
    return code_str if len(code_str) == 3 and code_str.isalpha() else None


def collect_written_codes(data: dict) -> Dict[str, str]:
    langs: Dict[str, str] = {}
    for lang_id, item in data.items():
        if not is_written_language(item):
            continue
        code = get_lang_code(lang_id, item)
        if code:
            langs[lang_id] = code
    return langs


def compute_distance_matrix(codes: List[str]) -> tuple[np.ndarray, set[str]]:
    n = len(codes)

    try:
        available = set(l2v.available_languages())
        valid_codes = [c for c in codes if c in available]
        log.info(
            "Found %d / %d languages in URIEL database. Fetching '%s'...",
            len(valid_codes), n, DISTANCE_TYPE,
        )
    except Exception as e:
        log.warning("Could not check available languages: %s", e)
        valid_codes = codes

    features_dict = {}
    if valid_codes:
        try:
            features_dict = l2v.get_features(valid_codes, DISTANCE_TYPE)
        except Exception as e:
            log.error("Failed to fetch lang2vec features: %s", e)

    if not features_dict:
        raise RuntimeError("lang2vec returned no features.")

    valid_list = [c for c in codes if c in features_dict and features_dict[c] is not None]
    valid_set = set(valid_list)
    log.info("Feature vectors available for %d/%d languages.", len(valid_list), n)

    if not valid_list:
        return np.full((n, n), np.nan), valid_set

    matrix_valid = np.array([features_dict[c] for c in valid_list], dtype=float)
    num_features = matrix_valid.shape[1]

    log.info("Computing pairwise distances via matrix dot product...")

    sum_ones = matrix_valid.sum(axis=1, keepdims=True)
    intersection = matrix_valid @ matrix_valid.T
    diff_count = sum_ones + sum_ones.T - 2 * intersection
    dist_matrix_valid = diff_count / num_features if num_features > 0 else np.zeros_like(diff_count)

    full_matrix = np.full((n, n), np.nan)
    code_to_idx = {c: i for i, c in enumerate(codes)}
    valid_indices = [code_to_idx[c] for c in valid_list]
    full_matrix[np.ix_(valid_indices, valid_indices)] = dist_matrix_valid

    return full_matrix, valid_set


class CheckpointManager:
    def __init__(self, path: Path = CHECKPOINT_PATH):
        self.path = path

    def load(self, distance_type: str):
        if not self.path.exists():
            return None
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("version") != 1:
                return None
            if data.get("distance_type") != distance_type:
                return None
            if data.get("glfm_version") != GLFM_VERSION:
                return None
            return data
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            return None

    def save(self, distance_type: str, completed: List[str], results: Dict[str, list]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "distance_type": distance_type,
            "distance_source": DISTANCE_SOURCE,
            "glfm_version": GLFM_VERSION,
            "completed": completed,
            "results": results,
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)

    def remove(self) -> None:
        if self.path.exists():
            self.path.unlink()


def build_nearest_map(data: dict, max_neighbors: int = MAX_NEIGHBORS) -> Dict[str, list]:
    langs = collect_written_codes(data)
    lang_ids = list(langs.keys())
    codes = [langs[lid] for lid in lang_ids]

    if not lang_ids:
        log.warning("No written languages with valid ISO 639-3 codes found!")
        return {}

    log.info("Computing '%s' distances for %d written languages (max %d per lang)...",
             DISTANCE_TYPE, len(lang_ids), max_neighbors)

    try:
        matrix, _ = compute_distance_matrix(codes)
    except Exception:
        log.exception("Batched lang2vec distance call failed for %d languages.", len(lang_ids))
        raise

    checkpoint = CheckpointManager()
    state = checkpoint.load(DISTANCE_TYPE)

    completed_list: List[str] = []
    results: Dict[str, list] = {}
    completed_set: set = set()

    if state is not None:
        tmp_completed = state.get("completed", [])
        tmp_results = state.get("results", {})
        if isinstance(tmp_completed, list):
            completed_list = tmp_completed
            completed_set = set(tmp_completed)
        if isinstance(tmp_results, dict):
            results = tmp_results
        log.info("Resuming from checkpoint. %d languages already processed.", len(completed_set))
    else:
        log.info("No checkpoint found. Starting fresh.")

    processed = len(completed_set)

    for i, lang_id in enumerate(lang_ids):
        if lang_id in completed_set:
            continue

        row = matrix[i]
        valid_mask = ~np.isnan(row)
        valid_mask[i] = False

        if not np.any(valid_mask):
            results[lang_id] = []
            completed_set.add(lang_id)
            completed_list.append(lang_id)
            processed += 1
            continue

        valid_indices = np.where(valid_mask)[0]
        valid_distances = row[valid_indices]

        distances = [
            {"lang": lang_ids[j], "distance": round(float(dist), 4)}
            for j, dist in zip(valid_indices, valid_distances)
        ]
        distances.sort(key=lambda x: x["distance"])

        results[lang_id] = distances[:max_neighbors]
        completed_set.add(lang_id)
        completed_list.append(lang_id)
        processed += 1

        if processed % CHECKPOINT_INTERVAL == 0 or processed == len(lang_ids):
            log.info("[%d/%d] %s (%.1f%%)", processed, len(lang_ids),
                     lang_id, (processed / len(lang_ids)) * 100)
            checkpoint.save(DISTANCE_TYPE, completed_list, results)

    checkpoint.save(DISTANCE_TYPE, completed_list, results)
    log.info("Completed processing nearest languages for %d languages.", processed)
    return results


def attach_metadata(data: dict) -> None:
    for lang_id, item in data.items():
        if not is_written_language(item):
            continue
        item["distance_source"] = DISTANCE_SOURCE
        item["distance_type"] = DISTANCE_TYPE
        item["distance_bases"] = DISTANCE_BASES


def run(input_path: Path, output_path: Path, do_backup: bool = True,
        max_neighbors: int = MAX_NEIGHBORS) -> None:
    data = load_json(input_path)
    nearest_map = build_nearest_map(data, max_neighbors=max_neighbors)

    for lang_id, nearest in nearest_map.items():
        if lang_id in data:
            data[lang_id]["nearest_languages"] = nearest

    attach_metadata(data)

    if output_path == input_path and do_backup:
        make_backup(input_path)

    save_json(output_path, data)
    CheckpointManager().remove()
    log.info("Wrote nearest_languages for %d languages to %s",
             len(nearest_map), output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Attach nearest-language data to unified_languages.json",
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_FILE)
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Oletus: ylikirjoittaa --input (backup tehdään ensin)",
    )
    parser.add_argument(
        "--no-backup", action="store_true",
        help="Ohita backup ennen ylikirjoitusta",
    )
    parser.add_argument(
        "--max-neighbors", type=int, default=MAX_NEIGHBORS,
        help=f"Naapureiden enimmäismäärä per kieli (oletus: {MAX_NEIGHBORS})",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    output_path = args.output or args.input
    run(args.input, output_path,
        do_backup=not args.no_backup,
        max_neighbors=args.max_neighbors)


if __name__ == "__main__":
    main()
