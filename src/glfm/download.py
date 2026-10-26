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
# Lataa ladattavan datan (~/.cache/glfm/data/).
# Käyttö:
#     python3 -m glfm.download
#     python3 -m glfm.download --force
#     python3 -m glfm.download --target /tmp/glfm-data
#

import argparse
import hashlib
import io
import logging
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

log = logging.getLogger(__name__)


def download_data(force: bool = False) -> Path:
    """
    Lataa datan cacheen (~/.cache/glfm/data/).

    Args:
        force: pakota uudelleenlataus, vaikka data olisi jo olemassa

    Returns:
        Polku data-hakemistoon
    """
    from glfm.config import load_config
    from glfm.paths import get_cache_dir

    config = load_config()
    cache = get_cache_dir() / "data"

    if cache.exists() and not force:
        log.info("Data jo olemassa: %s", cache)
        return cache

    url = config["download"]["url"]
    sha256 = config["download"]["sha256"]
    timeout = config["download"]["timeout"]

    log.info("Ladataan: %s", url)

    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = resp.read()
    except Exception as e:
        log.error("Lataus epäonnistui: %s", e)
        raise

    # Tarkista hash
    if sha256:
        h = hashlib.sha256(data).hexdigest()
        if h != sha256:
            raise RuntimeError(f"SHA256 ei täsmää: {h} != {sha256}")

    # Pura
    cache.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache.parent / "data.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            z.extractall(tmp)
    except zipfile.BadZipFile as e:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(f"Ladattu tiedosto ei ole kelvollinen zip: {e}")

    # Atominen uudelleennimeäminen
    if cache.exists():
        shutil.rmtree(cache)
    tmp.rename(cache)

    log.info("Valmis: %s", cache)
    return cache


def _data_size(path: Path) -> int:
    """Palauttaa hakemiston koon tavuina."""
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def main():
    parser = argparse.ArgumentParser(
        description="Lataa GLFM-data (~/.cache/glfm/data/).",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Pakota uudelleenlataus (ohita olemassa oleva data)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        path = download_data(force=args.force)
    except RuntimeError as e:
        log.error("%s", e)
        return 1

    size_kt = _data_size(path) / 1024
    print()
    print(f"Data: {path}")
    print(f"Koko: {size_kt:.1f} kt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
