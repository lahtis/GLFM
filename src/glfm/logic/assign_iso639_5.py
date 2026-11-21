"""Map Glottolog classifications to ISO 639-5 collection codes."""

import json
import logging
import re
import unicodedata
from functools import lru_cache
from typing import Any

from glfm.paths import get_bundled_data_dir

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_mapping() -> dict[str, dict[str, str]]:
    path = get_bundled_data_dir() / "iso639_5_glottolog_map.json"
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("Could not load ISO 639-5 Glottolog map %s: %s", path, exc)
        return {"glottocodes": {}, "families": {}}

    return {
        "glottocodes": raw.get("glottocodes", {}),
        "families": {
            _normalize_name(name): code
            for name, code in raw.get("families", {}).items()
            if isinstance(name, str) and isinstance(code, str)
        },
    }


def _normalize_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    plain = "".join(
        char for char in decomposed
        if not unicodedata.combining(char)
    )
    plain = re.sub(r"\b(languages?|families|groups?)\b", "", plain)
    return re.sub(r"[^a-z0-9]+", "", plain)


def assign_iso639_5(
    glottolog: dict[str, Any],
    iso639_5_groups: dict[str, dict[str, Any]],
) -> str:
    """Return the mapped ISO 639-5 code, or empty if no curated link exists.

    Glottolog lineage is checked from the most specific languoid upward.
    The family-name map is used when lineage is not available (for example,
    metadata returned by the Wikidata fallback).
    """
    mapping = _load_mapping()
    valid_codes = set(iso639_5_groups)

    # Match identical family names automatically; ambiguous ISO labels are
    # excluded and can be resolved explicitly in the curated map.
    by_name: dict[str, set[str]] = {}
    for code, record in iso639_5_groups.items():
        name = record.get("name", "")
        if isinstance(name, str) and name:
            by_name.setdefault(_normalize_name(name), set()).add(code)
    exact_names = {
        name: next(iter(codes))
        for name, codes in by_name.items()
        if len(codes) == 1
    }

    lineage = glottolog.get("lineage", [])
    candidates = list(lineage) if isinstance(lineage, list) else []
    glottocode = glottolog.get("glottocode")
    if isinstance(glottocode, str) and glottocode:
        candidates.insert(0, glottocode)

    for code in candidates:
        mapped = mapping["glottocodes"].get(code)
        if mapped in valid_codes:
            return mapped

    lineage_names = glottolog.get("lineage_names", [])
    if isinstance(lineage_names, list):
        for name in lineage_names:
            if not isinstance(name, str):
                continue
            mapped = mapping["families"].get(_normalize_name(name))
            if mapped in valid_codes:
                return mapped
            mapped = exact_names.get(_normalize_name(name))
            if mapped in valid_codes:
                return mapped

    family = glottolog.get("family")
    if isinstance(family, str):
        mapped = mapping["families"].get(_normalize_name(family))
        if mapped in valid_codes:
            return mapped
        mapped = exact_names.get(_normalize_name(family))
        if mapped in valid_codes:
            return mapped
    return ""
