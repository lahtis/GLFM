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

import csv
import importlib.util
import logging
from pathlib import Path
from typing import Any, Dict

from glfm.errors import DataError, OperationalError
from glfm.paths import get_data_dir

log = logging.getLogger(__name__)


def _load_data_module(name: str):
    """Load a .py module from the data directory (e.g. iso_639_1.py).

    Returns None if the file is missing.
    """
    path = get_data_dir() / f"{name}.py"
    if not path.exists():
        log.debug("Data module missing: %s", path)
        return None

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        log.warning("Could not load module: %s", path)
        return None

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except (SyntaxError, ImportError) as e:
        raise DataError(
            f"Could not execute {path}: {e}",
            source=name,
        ) from e
    return module


def _safe(obj, key, default=""):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def _as_list(v) -> list:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        return [v]
    return []


def load_sil_types() -> Dict[str, str]:
    """Read the SIL Language_Type column from iso_639_3.tab.

    Returns {iso639_3: language_type}, e.g. {"fin": "L", "lat": "H"}.
    """
    sil_file = get_data_dir() / "iso_639_3.tab"

    if not sil_file.exists():
        log.warning(
            "iso_639_3.tab missing (%s) - language_type will be empty",
            sil_file,
        )
        return {}

    types: Dict[str, str] = {}
    try:
        with open(sil_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                code = row.get("Id", "").strip()
                ltype = row.get("Language_Type", "").strip()
                if code and ltype:
                    types[code] = ltype
    except OSError as e:
        raise OperationalError(
            f"Could not read {sil_file}: {e}",
            source="iso_639_3",
            kind="transport",
        ) from e
    except csv.Error as e:
        raise DataError(
            f"Could not parse {sil_file}: {e}",
            source="iso_639_3",
        ) from e

    log.info("Loaded %d SIL Language_Type values", len(types))
    return types


def load_iso_639() -> Dict[str, Any]:
    """Return only ISO 639-3 languages with SIL Language_Type.

    Data is loaded from get_data_dir() (repo root / data or
    ~/.cache/glfm/data).
    """
    mod1 = _load_data_module("iso_639_1")
    mod2 = _load_data_module("iso_639_2")
    mod3 = _load_data_module("iso_639_3")
    mod_names = _load_data_module("iso_639_3_names")
    mod_macro = _load_data_module("iso_639_3_macrolanguages")

    if mod3 is None:
        data_dir = get_data_dir()
        raise OperationalError(
            f"iso_639_3.py missing: {data_dir / 'iso_639_3.py'}. "
            f"Run first: python3 -m glfm.tools.generate_iso_files",
            source="iso_639_3",
            kind="transport",
        )

    iso_639_1 = getattr(mod1, "iso_639_1", {}) if mod1 else {}
    iso_639_2 = getattr(mod2, "iso_639_2", {}) if mod2 else {}
    iso_639_3 = getattr(mod3, "iso_639_3", {})
    iso_639_3_names = (
        getattr(mod_names, "iso_639_3_names", {}) if mod_names else {}
    )
    iso_639_3_macrolanguages = (
        getattr(mod_macro, "iso_639_3_macrolanguages", {})
        if mod_macro else {}
    )

    if not isinstance(iso_639_3, dict):
        raise DataError(
            f"iso_639_3 should be a dict, got "
            f"{type(iso_639_3).__name__}",
            source="iso_639_3",
        )

    sil_types = load_sil_types()
    unified: Dict[str, Any] = {}

    # --- ISO 639-3: base languages ---
    for code3, info3 in iso_639_3.items():
        unified[code3] = {
            "name": _safe(info3, "name", code3),
            "iso639_1": _safe(info3, "iso639_1", ""),
            "iso639_2B": _safe(info3, "iso639_2B", ""),
            "iso639_2T": _safe(info3, "iso639_2T", ""),
            "iso639_3": code3,
            "iso639_5": "",
            "language_type": sil_types.get(code3, ""),
            "aliases": _as_list(iso_639_3_names.get(code3)),
            "macrolanguages": _as_list(
                iso_639_3_macrolanguages.get(code3)
            ),
        }

    # --- ISO 639-2: ensure 2-letter codes ---
    for code3, info2 in iso_639_2.items():
        if code3 not in unified:
            log.debug(
                "ISO 639-2 code %s not in 639-3 (collective)", code3
            )
            continue
        unified[code3]["iso639_2B"] = _safe(
            info2, "iso639_2B", unified[code3]["iso639_2B"]
        )
        unified[code3]["iso639_2T"] = _safe(
            info2, "iso639_2T", unified[code3]["iso639_2T"]
        )

    # --- ISO 639-1: ensure 1-letter codes ---
    count_iso1 = 0
    for code1, value in iso_639_1.items():
        if isinstance(value, dict):
            code3 = value.get("iso639_3")
        elif isinstance(value, str):
            code3 = value
        else:
            log.warning(
                "iso_639_1[%s] unknown type (%s) - skipping",
                code1, type(value).__name__,
            )
            continue

        if code3 and code3 in unified:
            unified[code3]["iso639_1"] = code1
            count_iso1 += 1

    log.info(
        "Loaded %d ISO 639-3 languages, %d got ISO 639-1 code",
        len(unified), count_iso1,
    )
    return unified


def load_iso_639_5() -> Dict[str, Any]:
    """ISO 639-5 families separately (not in the language list)."""
    mod5 = _load_data_module("iso_639_5")
    if mod5 is None:
        return {}

    iso_639_5 = getattr(mod5, "iso_639_5", {})

    families: Dict[str, Any] = {}
    for family_code, info5 in iso_639_5.items():
        families[family_code] = {
            "name": _safe(info5, "name", family_code),
            "iso639_5": family_code,
        }
    log.info("Loaded %d ISO 639-5 language families", len(families))
    return families
