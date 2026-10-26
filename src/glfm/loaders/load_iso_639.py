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

import csv
import importlib.util
import logging
from pathlib import Path
from typing import Any, Dict

from glfm.paths import get_data_dir

log = logging.getLogger(__name__)


def _load_data_module(name: str):
    """
    Lataa .py-moduuli data/-hakemistosta (esim. iso_639_1.py).

    Palauttaa None jos tiedosto puuttuu.
    """
    path = get_data_dir() / f"{name}.py"
    if not path.exists():
        log.debug("Data-moduuli puuttuu: %s", path)
        return None

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        log.warning("Ei voi ladata moduulia: %s", path)
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
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
    """
    Lukee SIL:n iso_639_3.tab-tiedostosta Language_Type-sarakkeen.

    Palauttaa {iso639_3: language_type}, esim. {"fin": "L", "lat": "H"}.
    """
    sil_file = get_data_dir() / "iso_639_3.tab"

    if not sil_file.exists():
        log.warning("iso_639_3.tab puuttuu (%s) – language_type jää tyhjäksi",
                    sil_file)
        return {}

    types: Dict[str, str] = {}
    with open(sil_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            code = row.get("Id", "").strip()
            ltype = row.get("Language_Type", "").strip()
            if code and ltype:
                types[code] = ltype

    log.info("Ladattu %d SIL Language_Type -arvoa", len(types))
    return types


def load_iso_639() -> Dict[str, Any]:
    """
    Palauttaa vain ISO 639-3 -kielet SIL Language_Type -kentällä.

    Data ladataan get_data_dir()-hakemistosta (repo root / data
    tai ~/.cache/glfm/data).
    """
    # Lataa data-moduulit data/-hakemistosta
    mod1 = _load_data_module("iso_639_1")
    mod2 = _load_data_module("iso_639_2")
    mod3 = _load_data_module("iso_639_3")
    mod_names = _load_data_module("iso_639_3_names")
    mod_macro = _load_data_module("iso_639_3_macrolanguages")

    if mod3 is None:
        data_dir = get_data_dir()
        raise RuntimeError(
            f"iso_639_3.py puuttuu: {data_dir / 'iso_639_3.py'}\n"
            f"Aja ensin: python3 -m glfm.tools.generate_iso_files"
        )

    iso_639_1 = getattr(mod1, "iso_639_1", {}) if mod1 else {}
    iso_639_2 = getattr(mod2, "iso_639_2", {}) if mod2 else {}
    iso_639_3 = getattr(mod3, "iso_639_3", {})
    iso_639_3_names = getattr(mod_names, "iso_639_3_names", {}) if mod_names else {}
    iso_639_3_macrolanguages = (
        getattr(mod_macro, "iso_639_3_macrolanguages", {}) if mod_macro else {}
    )

    if not isinstance(iso_639_3, dict):
        raise TypeError(
            f"iso_639_3 pitäisi olla dict, on {type(iso_639_3).__name__}"
        )

    sil_types = load_sil_types()
    unified: Dict[str, Any] = {}

    # --- ISO 639-3: peruskielet ---
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
            "macrolanguages": _as_list(iso_639_3_macrolanguages.get(code3)),
        }

    # --- ISO 639-2: varmista 2-koodit ---
    for code3, info2 in iso_639_2.items():
        if code3 not in unified:
            log.debug("ISO 639-2 koodi %s ei ole 639-3:ssa (kollektiivinen)", code3)
            continue
        unified[code3]["iso639_2B"] = _safe(
            info2, "iso639_2B", unified[code3]["iso639_2B"]
        )
        unified[code3]["iso639_2T"] = _safe(
            info2, "iso639_2T", unified[code3]["iso639_2T"]
        )

    # --- ISO 639-1: varmista 1-koodit ---
    count_iso1 = 0
    for code1, value in iso_639_1.items():
        if isinstance(value, dict):
            code3 = value.get("iso639_3")
        elif isinstance(value, str):
            code3 = value
        else:
            log.warning(
                "iso_639_1[%s] tuntematon tyyppi (%s) – ohitetaan",
                code1, type(value).__name__,
            )
            continue

        if code3 and code3 in unified:
            unified[code3]["iso639_1"] = code1
            count_iso1 += 1

    log.info(
        "Ladattu %d ISO 639-3 -kieltä, %d sai ISO 639-1 -koodin",
        len(unified), count_iso1,
    )
    return unified


def load_iso_639_5() -> Dict[str, Any]:
    """ISO 639-5 -perheet erillisenä (ei kielilistassa)."""
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
    log.info("Ladattu %d ISO 639-5 -kieliperhettä", len(families))
    return families
