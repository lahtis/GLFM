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
# Hakee ja lukee CLDR likelySubtags -datan.
# URL ja versio luetaan configista (glfm.config / config.toml / env).
#

import argparse
import gzip
import json
import logging
import sys
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _setup_imports() -> None:
    """Varmistaa että src/ on sys.path:ssä (kehitys)."""
    src = PROJECT_ROOT / "src"
    if src.exists() and str(src) not in sys.path:
        sys.path.insert(0, str(src))


_setup_imports()

from glfm.config import load_config
from glfm.paths import get_data_dir


def _get_cldr_config() -> dict:
    """Palauttaa CLDR-konfiguraation."""
    config = load_config()
    cldr = config.get("sources", {}).get("cldr", {})
    if not cldr.get("url"):
        raise RuntimeError(
            "Config: sources.cldr.url puuttuu. "
            "Tarkista config.toml tai GLFM_CLDR_URL."
        )
    return {
        "version": cldr.get("version", "unknown"),
        "url": cldr["url"],
        "user_agent": config.get("http", {}).get(
            "user_agent", "glfm/1.0.4"
        ),
        "timeout": config.get("http", {}).get("timeout", 60),
    }


def _cldr_local_file() -> Path:
    """Palauttaa CLDR-tiedoston polun (data/cldr/likelySubtags.json.gz)."""
    return get_data_dir() / "cldr" / "likelySubtags.json.gz"


def fetch_cldr_likely_subtags(force: bool = False) -> Path:
    """
    Hakee CLDR likelySubtags.json -tiedoston ja tallentaa gzipattuna.

    URL ja versio luetaan configista. Käytetään erikseen, kun halutaan
    päivittää data.

    Palauttaa tallennetun tiedoston polun.
    """
    cldr = _get_cldr_config()
    local_file = _cldr_local_file()

    if local_file.exists() and not force:
        log.info("CLDR-data jo olemassa: %s", local_file)
        return local_file

    log.info("Ladataan CLDR %s: %s", cldr["version"], cldr["url"])

    req = urllib.request.Request(
        cldr["url"],
        headers={"User-Agent": cldr["user_agent"]},
    )

    try:
        with urllib.request.urlopen(req, timeout=cldr["timeout"]) as resp:
            data = resp.read()
    except Exception as e:
        raise RuntimeError(
            f"CLDR-lataus epäonnistui: {e}. "
            f"Tarkista verkko tai aseta data manuaalisesti: {local_file}"
        ) from e

    # Atominen kirjoitus: tmp + rename
    local_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = local_file.with_suffix(".tmp")
    with gzip.open(tmp, "wb") as f:
        f.write(data)
    tmp.replace(local_file)

    log.info("Tallennettu: %s (%.1f kt)", local_file,
             local_file.stat().st_size / 1024)
    return local_file


def load_cldr_likely_subtags() -> dict:
    """
    Lukee bundled CLDR likelySubtags -datan.

    Palauttaa dictin muodossa: {"fi": "fi-Latn-FI", ...}
    (CLDR 48+ käyttää väliviivoja, ei alaviivoja.)

    EI koske verkkoon, jos tiedosto on olemassa. Jos tiedosto puuttuu,
    yrittää hakea sen kerran (fetch_cldr_likely_subtags).
    """
    local_file = _cldr_local_file()

    if not local_file.exists():
        log.warning("CLDR-data puuttuu, yritetään hakea: %s", local_file)
        try:
            fetch_cldr_likely_subtags()
        except RuntimeError as e:
            log.error("CLDR-dataa ei saatu: %s", e)
            raise

    with gzip.open(local_file, "rt", encoding="utf-8") as f:
        raw = json.load(f)

    subtags = raw.get("supplemental", {}).get("likelySubtags", {})
    if not subtags:
        raise RuntimeError(
            f"CLDR-tiedosto {local_file} ei sisällä likelySubtags-dataa"
        )

    log.info("Ladattu %d CLDR likelySubtags -sääntöä", len(subtags))
    return subtags


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Hae CLDR likelySubtags.json gzipattuna.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Pakota uudelleenlataus (ohita olemassa oleva tiedosto)",
    )
    args = parser.parse_args()

    try:
        path = fetch_cldr_likely_subtags(force=args.force)
    except RuntimeError as e:
        log.error("%s", e)
        return 1

    print(f"Valmis: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
