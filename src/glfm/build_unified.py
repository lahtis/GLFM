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

import gzip
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from glfm.config import load_config
from glfm.errors import DataError, OperationalError
from glfm.loaders.load_cldr_likely_subtags import (
    load_cldr_likely_subtags,
)
from glfm.loaders.load_glottolog import load_glottolog
from glfm.loaders.load_iso_639 import load_iso_639
from glfm.loaders.load_override_scripts import load_override_scripts
from glfm.loaders.load_pos_stats import load_pos_stats
from glfm.loaders.load_uralic_languages import load_uralic_languages
from glfm.loaders.load_wiktionary_languages import (
    load_wiktionary_languages,
)
from glfm.loaders.load_written_languages import load_written_languages
from glfm.logic.build_bcp47 import build_bcp47
from glfm.logic.decide_default_region import decide_default_region
from glfm.logic.decide_default_script import decide_default_script
from glfm.logic.decide_fallback import decide_fallback
from glfm.logic.is_uralic import is_uralic
from glfm.logic.set_uralic_langs import set_uralic_langs
from glfm.models.language import Language
from glfm.paths import get_data_dir

log = logging.getLogger(__name__)

# Distance and source metadata (URIEL / lang2vec).
DISTANCE_SOURCE = "lang2vec / URIEL"
DISTANCE_TYPE = "fam"
DISTANCE_BASES = ["WALS", "SSWL", "PHOIBLE", "Ethnologue", "Glottolog"]


# ---------------------------------------------------------
# Build unified structure
# ---------------------------------------------------------

def build_unified(config: dict) -> Dict[str, Any]:
    # --- Load data sources ---
    iso = load_iso_639()
    cldr = load_cldr_likely_subtags(config)
    wikt = load_wiktionary_languages()
    written = load_written_languages()
    uralic_set = load_uralic_languages()
    glottolog = load_glottolog()
    pos_stats = load_pos_stats()
    overrides = load_override_scripts()

    if not uralic_set:
        log.warning(
            "uralic_languages.json missing or empty - "
            "all uralicNLP flags will be False"
        )

    set_uralic_langs(uralic_set)

    unified: Dict[str, Any] = {}

    # --- Iterate over all ISO languages ---
    for lang_id, iso_info in iso.items():
        w = wikt.get(lang_id, {})
        w_written = written.get(lang_id, {})
        glotto = glottolog.get(lang_id, {})
        pos = pos_stats.get(lang_id, {})

        # Names
        name = w.get("name") or iso_info.get("name") or lang_id
        official_name = w.get("official_name") or name

        # ISO codes
        iso1 = iso_info.get("iso639_1", "")
        iso2B = iso_info.get("iso639_2B", "")
        iso2T = iso_info.get("iso639_2T", "")
        iso3 = iso_info.get("iso639_3", "")
        iso5 = iso_info.get("iso639_5", "")
        language_type = iso_info.get("language_type", "")

        # --- Script and region dynamically from sources ---
        script = decide_default_script(
            lang_id, w, cldr, w_written, iso_info, overrides
        )
        region = decide_default_region(lang_id, w, cldr, iso_info)

        # --- Written status is determined SOLELY by verified script ---
        is_written_flag = bool(
            script and script.upper() != "UNKNOWN"
        )
        scripts = [script] if is_written_flag else []

        # --- BCP-47 ---
        bcp47 = build_bcp47(
            lang_id,
            script if is_written_flag else "",
            region,
            iso_info,
        )

        # --- Fallback and Uralic support ---
        fallback = decide_fallback(lang_id, w)
        uralic = is_uralic(lang_id)

        # --- Glottolog fields ---
        glottocode = (
            glotto.get("glottocode")
            or w_written.get("glottocode", "")
        )
        family = (
            glotto.get("family")
            or w_written.get("family", "")
        )

        # Create Language object
        lang_obj = Language(
            id=lang_id,
            name=name,
            official_name=official_name,
            iso639_1=iso1,
            iso639_2B=iso2B,
            iso639_2T=iso2T,
            iso639_3=iso3,
            iso639_5=iso5,
            language_type=language_type,
            default_script=script if is_written_flag else "",
            default_region=region,
            bcp47=bcp47,
            fallback=fallback,
            uralicNLP=uralic,
            written=is_written_flag,
            written_scripts=scripts,
            glottocode=glottocode,
            family=family,
            glottolog=glotto,
            pos_stats=pos,
        )

        lang_dict = lang_obj.to_dict()

        # --- Distance metadata: ALWAYS present, not only for written.
        #     Written languages get a neighbor list (filled later by
        #     compute_nearest_languages.py).
        lang_dict["distance_source"] = DISTANCE_SOURCE
        lang_dict["distance_type"] = DISTANCE_TYPE
        lang_dict["distance_bases"] = DISTANCE_BASES
        lang_dict["nearest_languages"] = []

        unified[lang_id] = lang_dict

    return unified


# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Atomic binary write."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)
    except OSError as e:
        raise OperationalError(
            f"Could not write {path}: {e}",
            source="filesystem",
            kind="transport",
        ) from e


def _save(unified: Dict[str, Any]) -> None:
    """Save both pretty JSON (debug) and gzip JSON (production)."""
    output_root = get_data_dir()
    output = output_root / "unified_languages.json"
    output_gz = output_root / "unified_languages.json.gz"

    # Pretty (debug)
    try:
        pretty = json.dumps(
            unified, ensure_ascii=False, indent=2
        ).encode("utf-8")
    except (TypeError, ValueError) as e:
        raise DataError(
            f"Could not serialise unified data: {e}",
            source="unified_languages.json",
        ) from e
    _atomic_write_bytes(output, pretty)
    log.info(
        "Written: %s (%.1f MB)",
        output, output.stat().st_size / 1e6,
    )

    # Gzip (production, small)
    try:
        compact = json.dumps(
            unified, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    except (TypeError, ValueError) as e:
        raise DataError(
            f"Could not serialise unified data for gzip: {e}",
            source="unified_languages.json",
        ) from e
    _atomic_write_bytes(output_gz, gzip.compress(compact))
    log.info(
        "Written: %s (%.1f MB)",
        output_gz, output_gz.stat().st_size / 1e6,
    )


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        config = load_config()
        unified = build_unified(config)
    except OperationalError as exc:
        log.error("Source error: %s", exc)
        if exc.retryable:
            log.error("Error is temporary - try again later.")
        return 1
    except DataError as exc:
        log.error("Data error: %s", exc)
        return 1

    try:
        _save(unified)
    except (OperationalError, DataError) as exc:
        log.error("Save error: %s", exc)
        return 1

    log.info("Done: %d languages", len(unified))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
