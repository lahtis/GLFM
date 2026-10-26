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
# Lataa ISO 639 -lähteet ja generoi Python-moduulit data/-hakemistoon.
# Tuottaa: iso_639_1.py, iso_639_2.py, iso_639_3.py,
#          iso_639_3_names.py, iso_639_3_macrolanguages.py, iso_639_5.py
#
# URL:t ja asetukset luetaan configista (glfm.config / config.toml /
# ympäristömuuttujat). Ei kovakoodattuja URL:ia.
#

import logging
import os
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


def fail(msg: str) -> None:
    log.error("%s", msg)
    sys.exit(1)


def _atomic_write_text(path: Path, content: str) -> None:
    """Atominen tekstikirjoitus."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def _get_source_config(config: dict, key: str) -> dict:
    """Palauttaa config['sources'][key] tai virheen."""
    sources = config.get("sources", {})
    if key not in sources:
        fail(f"Config: sources.{key} puuttuu")
    return sources[key]


def safe_download(
    url_key: str,
    config: dict,
    timeout: int | None = None,
) -> Path:
    """
    Lataa yhden lähteen configista ja tallentaa sen data/-hakemistoon.

    Args:
        url_key: config['sources'][key] – esim. "iso_639_3"
        config: load_config()-tulos
        timeout: ylikirjoittaa config['http']['timeout']
    """
    source = _get_source_config(config, url_key)
    url = source.get("url")
    if not url:
        fail(f"Config: sources.{url_key}.url puuttuu")

    http = config.get("http", {})
    user_agent = http.get("user_agent", "glfm/1.0.4")
    timeout = timeout or http.get("timeout", 60)

    data_dir = get_data_dir()
    suffix = ".rdf" if url_key == "iso_639_5" else ".tab"
    out = data_dir / f"{url_key}{suffix}"

    log.info("Ladataan %s: %s", url_key, url)

    req = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status != 200:
                fail(f"HTTP {response.status} ladattaessa {url_key}")
            content = response.read()
    except Exception as e:
        fail(f"Virhe ladattaessa {url_key}: {e}")

    if len(content) < 500:
        fail(f"Ladattu tiedosto liian pieni ({len(content)} tavua): {url_key}")

    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        with open(out, "wb") as f:
            f.write(content)
    except Exception as e:
        fail(f"Virhe tallennettaessa {out}: {e}")

    log.info("Tallennettu: %s (%.1f kt)", out, len(content) / 1024)
    return out


def generate_iso_modules() -> None:
    config = load_config()
    data_dir = get_data_dir()

    log.info("=== Ladataan ISO-lähteet ===")
    log.info("Data-hakemisto: %s", data_dir)

    tab3 = safe_download("iso_639_3", config)
    tab_names = safe_download("iso_639_3_names", config)
    tab_macro = safe_download("iso_639_3_macrolanguages", config)
    rdf5 = safe_download("iso_639_5", config)

    log.info("=== Parsitaan ISO-tiedostot ===")

    # Importoi parse_iso_files sekä src/:stä että tools/:sta
    try:
        from glfm.tools.parse_iso_files import parse_all_iso_files
    except ImportError:
        try:
            from glfm.tools.parse_iso_files import parse_all_iso_files
        except ImportError:
            sys.path.insert(0, str(Path(__file__).parent))
            from glfm.tools.parse_iso_files import parse_all_iso_files

    try:
        data = parse_all_iso_files(tab3, tab_names, tab_macro, rdf5)
    except Exception as e:
        fail(f"Virhe parsinnassa: {e}")

    log.info("=== Kirjoitetaan Python-moduulit data/-hakemistoon ===")

    modules = {
        "iso_639_1.py": f"iso_639_1 = {data['iso639_1']}\n",
        "iso_639_2.py": f"iso_639_2 = {data['iso639_2']}\n",
        "iso_639_3.py": f"iso_639_3 = {data['iso639_3']}\n",
        "iso_639_3_names.py": f"iso_639_3_names = {data['iso639_3_names']}\n",
        "iso_639_3_macrolanguages.py": (
            f"iso_639_3_macrolanguages = {data['iso639_3_macrolanguages']}\n"
        ),
        "iso_639_5.py": f"iso_639_5 = {data['iso639_5']}\n",
    }

    try:
        for name, content in modules.items():
            _atomic_write_text(data_dir / name, content)
            log.info("Kirjoitettu: %s", name)
    except Exception as e:
        fail(f"Virhe kirjoitettaessa: {e}")

    log.info("Kaikki ISO-moduulit generoitu onnistuneesti.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )
    generate_iso_modules()
