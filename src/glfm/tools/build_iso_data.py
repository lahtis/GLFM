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
# HUOM: Tämä skripti tuottaa .json-tiedostot (data/iso_639_*.json).
# load_iso_639.py lukee .py-moduulit (data/iso_639_*.py).
# Nämä EIVÄT ole sama asia. Jos et tarvitse .json-tiedostoja,
# älä aja tätä skriptiä.
#

import argparse
import csv
import json
import logging
import os
import urllib.request
from pathlib import Path

from glfm.paths import get_data_dir, get_output_dir

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = get_data_dir()

ISO1_OUT = DATA_ROOT / "iso_639_1.json"
ISO2_OUT = DATA_ROOT / "iso_639_2.json"
ISO3_OUT = DATA_ROOT / "iso_639_3.json"

ISO_639_3_URL = "https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3.tab"
ISO_639_2_URL = "https://www.loc.gov/standards/iso639-2/ISO-639-2_utf-8.txt"
ISO_639_1_URL = "https://datahub.io/core/language-codes/r/language-codes.csv"


def download(url: str, path: Path, timeout: int = 60) -> None:
    """Lataa tiedoston, käyttää fallback-mirroria ISO 639-3:lle."""
    log.info("Ladataan: %s", url)

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "glfm/1.0.2 (https://codeberg.org/lahtis/GLFM)"},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()
        path.write_bytes(data)
        log.info("Tallennettu: %s (%.1f kt)", path, len(data) / 1024)
        return
    except Exception as e:
        log.warning("Ensisijainen lataus epäonnistui: %s", e)

    if "iso-639-3.tab" in url:
        fallback_url = (
            "https://raw.githubusercontent.com/haliaeetus/iso-639/"
            "master/data/iso-639-3.tab"
        )
        log.info("Kokeillaan fallback-mirroria: %s", fallback_url)
        req2 = urllib.request.Request(
            fallback_url, headers={"User-Agent": "glfm/1.0.2"}
        )
        with urllib.request.urlopen(req2, timeout=timeout) as response:
            data = response.read()
        path.write_bytes(data)
        log.info("Tallennettu fallbackista: %s", path)
        return

    raise RuntimeError(f"Lataus epäonnistui: {url}")


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def build_iso_639_3() -> None:
    """Rakentaa iso_639_3.json SIL:n .tab-tiedostosta."""
    tmp = DATA_ROOT / "iso-639-3.tab"
    download(ISO_639_3_URL, tmp)

    iso3: dict = {}
    with open(tmp, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            code3 = (row.get("Id") or "").strip()
            if not code3:
                continue

            iso2B = (row.get("Part2_B") or row.get("Part2B") or "").strip()
            iso2T = (row.get("Part2_T") or row.get("Part2T") or "").strip()
            iso1 = (row.get("Part1") or "").strip()

            iso3[code3] = {
                "name": (row.get("Ref_Name") or "").strip(),
                "iso639_3": code3,
                "iso639_2B": iso2B,
                "iso639_2T": iso2T,
                "iso639_1": iso1,
                "iso639_5": "",
            }

    _atomic_write_json(ISO3_OUT, iso3)
    log.info("Rakennettu: %s (%d kieltä)", ISO3_OUT, len(iso3))


def build_iso_639_2() -> None:
    """Rakentaa iso_639_2.json Library of Congressin listasta."""
    tmp = DATA_ROOT / "iso-639-2.txt"
    download(ISO_639_2_URL, tmp)

    iso2: dict = {}
    with open(tmp, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) < 4:
                continue

            code2B, code2T, code1, name = [p.strip() for p in parts[:4]]
            key = code2T or code2B
            if not key:
                continue

            iso2[key] = {
                "name": name,
                "iso639_2B": code2B,
                "iso639_2T": code2T,
                "iso639_1": code1,
                "iso639_3": "",
            }

    _atomic_write_json(ISO2_OUT, iso2)
    log.info("Rakennettu: %s (%d kieltä)", ISO2_OUT, len(iso2))


def build_iso_639_1() -> None:
    """Rakentaa iso_639_1.json DataHubin CSV:stä."""
    tmp = DATA_ROOT / "language-codes.csv"
    download(ISO_639_1_URL, tmp)

    iso1: dict = {}
    with open(tmp, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code1 = (
                row.get("alpha2") or row.get("Alpha2")
                or row.get("ISO639-1") or ""
            ).strip()
            if not code1:
                continue

            code3 = (
                row.get("alpha3-b") or row.get("alpha3")
                or row.get("Alpha3") or row.get("ISO639-2B")
                or row.get("ISO639-3") or ""
            ).strip()
            name = (
                row.get("English") or row.get("Name")
                or row.get("name") or ""
            ).strip()

            iso1[code1] = {
                "name": name,
                "iso639_1": code1,
                "iso639_3": code3,
            }

    _atomic_write_json(ISO1_OUT, iso1)
    log.info("Rakennettu: %s (%d kieltä)", ISO1_OUT, len(iso1))


def main():
    parser = argparse.ArgumentParser(
        description="Lataa ja rakenna ISO 639 JSON-tiedostot (redundantti).",
    )
    parser.add_argument(
        "--skip-iso3", action="store_true", help="Ohita ISO 639-3"
    )
    parser.add_argument(
        "--skip-iso2", action="store_true", help="Ohita ISO 639-2"
    )
    parser.add_argument(
        "--skip-iso1", action="store_true", help="Ohita ISO 639-1"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    log.info("=== Rakennetaan ISO 639 JSON-tiedostot ===")
    if not args.skip_iso3:
        build_iso_639_3()
    if not args.skip_iso2:
        build_iso_639_2()
    if not args.skip_iso1:
        build_iso_639_1()
    log.info("=== Valmis ===")


if __name__ == "__main__":
    main()
