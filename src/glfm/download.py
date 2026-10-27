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
# Lataa datapaketin (~/.cache/glfm/data/).
# Käyttö:
#     python3 -m glfm.download                    # consumer (558 kt)
#     python3 -m glfm.download --tier research    # research (1.4 MB)
#     python3 -m glfm.download --force
#

import argparse
import gzip
import hashlib
import io
import json
import logging
import shutil
import sys
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

TIERS = ("consumer", "research")


def download_data(force: bool = False, tier: str = "consumer") -> Path:
    """
    Lataa datapaketin cacheen (~/.cache/glfm/data/).

    Args:
        force: pakota uudelleenlataus
        tier: "consumer" (558 kt) tai "research" (1.4 MB)

    Returns:
        Polku data-hakemistoon
    """
    from glfm.config import load_config
    from glfm.paths import get_cache_dir

    if tier not in TIERS:
        raise ValueError(f"Tuntematon tier: {tier}. Valinnat: {TIERS}")

    config = load_config()
    cache = get_cache_dir() / "data"

    # Tarkista onko jo ladattu
    marker = cache / f".downloaded_{tier}"
    if cache.exists() and marker.exists() and not force:
        log.info("Data (%s) jo olemassa: %s", tier, cache)
        return cache

    # Hae tier-kohtainen config
    download_cfg = config["download"].get(tier)
    if not download_cfg:
        raise RuntimeError(
            f"Config: download.{tier} puuttuu. "
            f"Tarkista config.toml."
        )

    # Kokeile ensisijaista URL:ia, sitten peilejä
    urls = [download_cfg["url"]]
    for name, url in download_cfg.get("mirrors", {}).items():
        if url != download_cfg["url"]:
            urls.append(url)

    data = None
    last_error = None

    for url in urls:
        try:
            log.info("Ladataan (%s): %s", tier, url)
            with urllib.request.urlopen(
                url, timeout=download_cfg["timeout"]
            ) as resp:
                data = resp.read()
            log.info("Ladattu (%s): %.1f kt", tier, len(data) / 1024)
            break
        except Exception as e:
            log.warning("Lataus epäonnistui (%s): %s", url, e)
            last_error = e
            continue

    if data is None:
        raise RuntimeError(f"Kaikki lataukset epäonnistuivat: {last_error}")

    # Tarkista hash
    if sha256 := download_cfg.get("sha256"):
        h = hashlib.sha256(data).hexdigest()
        if h != sha256:
            raise RuntimeError(f"SHA256 ei täsmää: {h} != {sha256}")

    # Pura gzip → JSON
    cache.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache.parent / f"data_{tier}.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()

    try:
        with gzip.open(io.BytesIO(data), "rt", encoding="utf-8") as gz:
            parsed = json.load(gz)
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(f"Purku epäonnistui: {e}")

    # Tallenna purettu JSON
    filename = (
        "languages_top20.json" if tier == "consumer"
        else "unified_languages.json"
    )
    output = tmp / filename
    with open(output, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False)

    # Atominen uudelleennimeäminen
    if cache.exists():
        shutil.rmtree(cache)
    tmp.rename(cache)

    # Merkitse ladatuksi
    (cache / f".downloaded_{tier}").touch()

    log.info("Valmis (%s): %s (%d kieltä)", tier, cache, len(parsed))
    return cache


def _data_size(path: Path) -> int:
    """Palauttaa hakemiston koon tavuina."""
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def main():
    parser = argparse.ArgumentParser(
        description="Lataa GLFM-data (~/.cache/glfm/data/).",
    )
    parser.add_argument(
        "--tier", choices=TIERS, default="consumer",
        help="Datapaketti: consumer (558 kt) tai research (1.4 MB)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Pakota uudelleenlataus",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        path = download_data(force=args.force, tier=args.tier)
    except (RuntimeError, ValueError) as e:
        log.error("%s", e)
        return 1

    size_kt = _data_size(path) / 1024
    print()
    print(f"Data ({args.tier}): {path}")
    print(f"Koko: {size_kt:.1f} kt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
