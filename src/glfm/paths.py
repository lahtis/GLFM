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

import os
from pathlib import Path

def get_cache_dir() -> Path:
    """Käyttäjän välimuisti (ladattava data)."""
    from glfm.config import load_config

    config = load_config()

    # 1. config.toml / env
    if cache_dir := config["paths"]["cache_dir"]:
        return Path(cache_dir).expanduser().resolve()

    # 2. XDG
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / config["paths"]["cache_dir_name"]

    # 3. Oletus
    return Path.home() / ".cache" / config["paths"]["cache_dir_name"]


def get_data_dir() -> Path:
    """
    Ladattava data (iso_639_3, glottolog, cldr, ...).

    Palauttaa AINA cache-hakemiston – ei repossa olevaa data/.
    Data luodaan/generoidaan tähän hakemistoon.
    """
    from glfm.config import load_config

    config = load_config()

    # 1. config.toml / env
    if data_dir := config["paths"]["data_dir"]:
        return Path(data_dir).expanduser().resolve()

    # 2. Cache (aina)
    return get_cache_dir() / config["paths"]["data_subdir"]


def get_bundled_data_dir() -> Path:
    """Sisäinen data (override_scripts, uralic_languages)."""
    return Path(__file__).resolve().parent / "data"


def get_output_dir() -> Path:
    """
    Output-hakemisto (unified, validation, logs).

    Oletus: cache/output (ladattava/generoitu data).
    Kehityksessä: repo root / output.
    """
    if env := os.environ.get("GLFM_OUTPUT_DIR"):
        return Path(env).expanduser().resolve()

    # Kehitys: repo root / output
    # paths.py on src/glfm/paths.py → parent.parent.parent = repo root
    return Path(__file__).resolve().parent.parent.parent / "output"
