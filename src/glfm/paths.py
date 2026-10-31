#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.1.0
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#

import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _get_cache_dir_cached() -> Path:
    """Internal: resolve cache dir once and cache it."""
    from glfm.config import load_config

    config = load_config()

    if cache_dir := config["paths"]["cache_dir"]:
        return Path(cache_dir).expanduser().resolve()

    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / config["paths"]["cache_dir_name"]

    return Path.home() / ".cache" / config["paths"]["cache_dir_name"]


def get_cache_dir() -> Path:
    """User cache (downloadable data)."""
    return _get_cache_dir_cached()


@lru_cache(maxsize=1)
def _get_data_dir_cached() -> Path:
    """Internal: resolve data dir once and cache it."""
    from glfm.config import load_config

    config = load_config()

    if data_dir := config["paths"]["data_dir"]:
        return Path(data_dir).expanduser().resolve()

    return get_cache_dir() / config["paths"]["data_subdir"]


def get_data_dir() -> Path:
    """Downloadable data (iso_639_3, glottolog, cldr, ...)."""
    return _get_data_dir_cached()


def get_bundled_data_dir() -> Path:
    """Bundled data (override_scripts, uralic_languages)."""
    return Path(__file__).resolve().parent / "data"
