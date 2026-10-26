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
# Konfiguraation lataus: config.toml + ympäristömuuttujat.
#

import copy
import logging
import os
from pathlib import Path

from glfm.paths import get_data_dir, get_output_dir

log = logging.getLogger(__name__)

# Oletuskonfiguraatio – ylikirjoitetaan config.toml:llä ja env-muuttujilla
DEFAULT_CONFIG = {
    "sources": {
        "iso_639_3": {
            "url": (
                "https://iso639-3.sil.org/sites/iso639-3/files/"
                "downloads/iso-639-3.tab"
            ),
        },
        "iso_639_3_names": {
            "url": (
                "https://iso639-3.sil.org/sites/iso639-3/files/"
                "downloads/iso-639-3_Name_Index.tab"
            ),
        },
        "iso_639_3_macrolanguages": {
            "url": (
                "https://iso639-3.sil.org/sites/iso639-3/files/"
                "downloads/iso-639-3-macrolanguages.tab"
            ),
        },
        "iso_639_5": {
            "url": "https://id.loc.gov/vocabulary/iso639-5.skos.rdf",
        },
        "cldr": {
            "version": "48.0.0",
            "url": (
                "https://raw.githubusercontent.com/unicode-org/"
                "cldr-json/48.0.0/cldr-json/cldr-core/supplemental/"
                "likelySubtags.json"
            ),
        },
        "wikidata": {
            "endpoint": "https://query.wikidata.org/sparql",
        },
    },
    "download": {
        "url": (
            "https://codeberg.org/lahtis/GLFM/releases/download/"
            "v1.0.4/data.zip"
        ),
        "sha256": "",
        "timeout": 300,
    },
    "http": {
        "user_agent": "glfm/1.0.4 (https://codeberg.org/lahtis/GLFM)",
        "timeout": 60,
    },
    "paths": {
        "cache_dir": "",
        "data_dir": "",
        "cache_dir_name": "glfm",
        "data_subdir": "data",
    },
    "logging": {
        "level": "INFO",
    },
}

# Ympäristömuuttujat → config-avaimet
ENV_MAP = {
    "GLFM_ISO_639_3_URL": ("sources", "iso_639_3", "url"),
    "GLFM_ISO_639_3_NAMES_URL": ("sources", "iso_639_3_names", "url"),
    "GLFM_ISO_639_3_MACRO_URL": ("sources", "iso_639_3_macrolanguages", "url"),
    "GLFM_ISO_639_5_URL": ("sources", "iso_639_5", "url"),
    "GLFM_CLDR_VERSION": ("sources", "cldr", "version"),
    "GLFM_CLDR_URL": ("sources", "cldr", "url"),
    "GLFM_WIKIDATA_ENDPOINT": ("sources", "wikidata", "endpoint"),
    "GLFM_DATA_URL": ("download", "url"),
    "GLFM_DATA_SHA256": ("download", "sha256"),
    "GLFM_DATA_TIMEOUT": ("download", "timeout"),
    "GLFM_USER_AGENT": ("http", "user_agent"),
    "GLFM_HTTP_TIMEOUT": ("http", "timeout"),
    "GLFM_CACHE_DIR": ("paths", "cache_dir"),
    "GLFM_DATA_DIR": ("paths", "data_dir"),
    "GLFM_LOG_LEVEL": ("logging", "level"),
}


def load_config() -> dict:
    """
    Lataa konfiguraation seuraavassa järjestyksessä:

      1. DEFAULT_CONFIG (kovakoodatut oletukset)
      2. config.toml (repon juuressa tai ~/.config/glfm/config.toml)
      3. Ympäristömuuttujat (GLFM_*)

    Palauttaa syvän kopion – ei jaa tilaa DEFAULT_CONFIG:n kanssa.
    """
    config = copy.deepcopy(DEFAULT_CONFIG)

    # 1. config.toml
    config_path = get_config_path()
    if config_path.exists():
        try:
            import tomllib
            with open(config_path, "rb") as f:
                user_config = tomllib.load(f)
            _merge(config, user_config)
            log.info("Luettu config: %s", config_path)
        except Exception as e:
            log.warning("Config-virhe (%s): %s", config_path, e)
    else:
        log.debug("config.toml puuttuu (%s), käytetään oletuksia",
                  config_path)

    # 2. Ympäristömuuttujat
    for env_key, path in ENV_MAP.items():
        if value := os.environ.get(env_key):
            _set_nested(config, path, value)
            log.debug("Env: %s → %s", env_key, ".".join(path))

    return config


def get_config_path() -> Path:
    """Palauttaa config.toml-polkua."""
    if env := os.environ.get("GLFM_CONFIG"):
        return Path(env).expanduser().resolve()

    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "glfm" / "config.toml"

    return Path.home() / ".config" / "glfm" / "config.toml"


def _set_nested(config: dict, path: tuple, value) -> None:
    """Asettaa arvon syvään dictiin."""
    current = config
    for key in path[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[path[-1]] = value


def _merge(base: dict, override: dict) -> None:
    """Syvä merge: override korvaa base:n arvot."""
    for key, value in override.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            _merge(base[key], value)
        else:
            base[key] = value
