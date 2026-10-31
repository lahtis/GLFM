#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.0.7
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
# Configuration loading: config.toml + environment variables.
#

import copy
import logging
import os
from pathlib import Path

from glfm._version import __version__

log = logging.getLogger(__name__)

# Version of the config structure (NOT the package version).
# Bump this when DEFAULT_CONFIG gains/removes/renames keys.
#
# History:
#   1 — initial: sources, download, http, paths, logging
#   2 — added nearest (distance_type, max_neighbors, decimals,
#       checkpoint_interval) and sources.wiktextract
#       (url, filename, timeout); download URLs → v1.0.7
CONFIG_VERSION = 2

# Default configuration — overridden by config.toml and env vars
DEFAULT_CONFIG = {
    "config_version": CONFIG_VERSION,
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
        "wiktextract": {
            "url": (
                "https://dumps.wikimedia.org/other/wiktextract/"
                "20260101/wiktextract-data.jsonl.gz"
            ),
            "filename": "raw-wiktextract-data.jsonl.gz",
            "timeout": 3600,
        },
    },
    "download": {
        "consumer": {
            "url": (
                "https://codeberg.org/lahtis/GLFM/releases/download/"
                "v.1.0.7/languages_top20.json.gz"
            ),
            "sha256": "",
            "size_kt": 558,
            "timeout": 300,
            "mirrors": {                
                "github": (
                    "https://github.com/lahtis/GLFM/releases/download/"
                    "v.1.0.7/languages_top20.json.gz"
                ),
            },
        },
        "research": {
            "url": (
                "https://codeberg.org/lahtis/GLFM/releases/download/"
                "v.1.0.7/unified_languages.json.gz"
            ),
            "sha256": "",
            "size_mb": 1.4,
            "timeout": 300,
            "mirrors": {                
                "github": (
                    "https://github.com/lahtis/GLFM/releases/download/"
                    "v.1.0.7/unified_languages.json.gz"
                ),
            },
        },
    },
    "nearest": {
        "distance_type": "syntax_knn",
        "max_neighbors": 100,
        "decimals": [4, 6],
        "checkpoint_interval": 1000,
    },
    "http": {
        # User-Agent built from version — not hardcoded
        "user_agent": f"glfm/{__version__} (https://codeberg.org/lahtis/GLFM)",
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

# Environment variables → config keys
ENV_MAP = {
    "GLFM_ISO_639_3_URL": ("sources", "iso_639_3", "url"),
    "GLFM_ISO_639_3_NAMES_URL": ("sources", "iso_639_3_names", "url"),
    "GLFM_ISO_639_3_MACRO_URL": ("sources", "iso_639_3_macrolanguages", "url"),
    "GLFM_ISO_639_5_URL": ("sources", "iso_639_5", "url"),
    "GLFM_CLDR_VERSION": ("sources", "cldr", "version"),
    "GLFM_CLDR_URL": ("sources", "cldr", "url"),
    "GLFM_WIKIDATA_ENDPOINT": ("sources", "wikidata", "endpoint"),
    "GLFM_WIKTEXTTRACT_URL": ("sources", "wiktextract", "url"),
    "GLFM_WIKTEXTTRACT_FILENAME": ("sources", "wiktextract", "filename"),
    "GLFM_WIKTEXTTRACT_TIMEOUT": ("sources", "wiktextract", "timeout"),
    "GLFM_CONSUMER_URL": ("download", "consumer", "url"),
    "GLFM_CONSUMER_SHA256": ("download", "consumer", "sha256"),
    "GLFM_CONSUMER_TIMEOUT": ("download", "consumer", "timeout"),
    "GLFM_RESEARCH_URL": ("download", "research", "url"),
    "GLFM_RESEARCH_SHA256": ("download", "research", "sha256"),
    "GLFM_RESEARCH_TIMEOUT": ("download", "research", "timeout"),
    "GLFM_NEAREST_DISTANCE_TYPE": ("nearest", "distance_type"),
    "GLFM_NEAREST_MAX_NEIGHBORS": ("nearest", "max_neighbors"),
    "GLFM_NEAREST_DECIMALS": ("nearest", "decimals"),
    "GLFM_NEAREST_CHECKPOINT_INTERVAL": ("nearest", "checkpoint_interval"),
    "GLFM_USER_AGENT": ("http", "user_agent"),
    "GLFM_HTTP_TIMEOUT": ("http", "timeout"),
    "GLFM_CACHE_DIR": ("paths", "cache_dir"),
    "GLFM_DATA_DIR": ("paths", "data_dir"),
    "GLFM_LOG_LEVEL": ("logging", "level"),
}


def load_config() -> dict:
    """
    Load configuration in the following order:

      1. DEFAULT_CONFIG (hardcoded defaults)
      2. config.toml (repo root or ~/.config/glfm/config.toml)
      3. Environment variables (GLFM_*)

    Returns a deep copy — does not share state with DEFAULT_CONFIG.
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
            log.info("Loaded config: %s", config_path)
        except Exception as e:
            log.warning("Config error (%s): %s", config_path, e)
    else:
        log.debug("config.toml missing (%s), using defaults", config_path)

    # 2. Check config_version
    _check_config_version(config, config_path)

    # 3. Environment variables
    for env_key, path in ENV_MAP.items():
        if value := os.environ.get(env_key):
            parsed = _parse_env_value(env_key, value)
            _set_nested(config, path, parsed)
            log.debug("Env: %s → %s", env_key, ".".join(path))

    return config


def get_config_path() -> Path:
    """Return config.toml path."""
    if env := os.environ.get("GLFM_CONFIG"):
        return Path(env).expanduser().resolve()

    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "glfm" / "config.toml"

    return Path.home() / ".config" / "glfm" / "config.toml"


def _check_config_version(config: dict, config_path: Path) -> None:
    """
    Warn if config.toml uses an older config_version than DEFAULT_CONFIG.

    The version is stored under the top-level `config_version` key.
    Missing key is treated as version 0 (pre-versioning).
    """
    user_version = config.get("config_version", 0)
    if not isinstance(user_version, int):
        log.warning(
            "config_version must be an integer, got %r. "
            "Assuming 0 (pre-versioning).",
            user_version,
        )
        user_version = 0

    if user_version < CONFIG_VERSION:
        log.warning(
            "config.toml is from an older config version "
            "(config_version=%d, current=%d). "
            "Missing keys will use defaults. "
            "See config.toml.example for the latest structure. "
            "(path: %s)",
            user_version, CONFIG_VERSION, config_path,
        )
    elif user_version > CONFIG_VERSION:
        log.warning(
            "config.toml uses a newer config version "
            "(config_version=%d, current=%d). "
            "Some settings may be ignored by this version of GLFM. "
            "(path: %s)",
            user_version, CONFIG_VERSION, config_path,
        )

    # Always ensure the effective config carries the current version
    config["config_version"] = CONFIG_VERSION


def _parse_env_value(key: str, value: str):
    """
    Parse an environment variable string into a typed value.

    - "decimals" → list of ints (comma-separated)
    - Integer-looking keys → int
    - Everything else → str
    """
    # decimals: "4,6" → [4, 6]
    if key.endswith("_DECIMALS"):
        try:
            return [int(x.strip()) for x in value.split(",") if x.strip()]
        except ValueError:
            log.warning("Invalid %s: %r, using raw string", key, value)
            return value

    # Integer-valued keys
    int_keys = (
        "_TIMEOUT", "_MAX_NEIGHBORS", "_CHECKPOINT_INTERVAL",
        "_SIZE_KT", "_SIZE_MB",
    )
    if any(key.endswith(suffix) for suffix in int_keys):
        try:
            return int(value)
        except ValueError:
            log.warning("Invalid %s: %r, using raw string", key, value)
            return value

    return value


def _set_nested(config: dict, path: tuple, value) -> None:
    """Set a value in a nested dict."""
    current = config
    for key in path[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[path[-1]] = value


def _merge(base: dict, override: dict) -> None:
    """Deep merge: override replaces base values."""
    for key, value in override.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            _merge(base[key], value)
        else:
            base[key] = value
