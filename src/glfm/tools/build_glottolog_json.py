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
# Fetch Glottolog metadata via Wikidata SPARQL.
# Alternative source: local languoids.json or languoids/tree/.
#
# Output: data/glottolog.json, keyed by ISO 639-3 code (e.g. "fin").
# Glottocode is a field, not a key.
#
# Wikidata endpoint, User-Agent and timeout are read from config.
# All outbound HTTP goes through glfm.utils.safe_http (vendored from SHL).
#

import argparse
import json
import logging
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

from glfm.config import load_config
from glfm.errors import DataError, OperationalError
from glfm.paths import get_data_dir
from glfm.utils.safe_http import safe_urlopen
from glfm.utils.safe_http_common import (
    SafeHTTPError,
    read_limited_response,
)

log = logging.getLogger(__name__)


# SPARQL responses for the full Glottolog can be a few MB.
# 50 MB is a generous upper bound.
MAX_SPARQL_RESPONSE_BYTES = 50 * 1024 * 1024


# --- Local sources (if present) ---

def load_from_languoids_json(path: Path) -> dict:
    """Read a local languoids.json file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        raise DataError(
            f"Invalid JSON in {path}: {e}",
            source="languoids.json",
        ) from e
    except OSError as e:
        raise OperationalError(
            f"Could not read {path}: {e}",
            source="languoids.json",
            kind="transport",
        ) from e

    if not isinstance(raw, list):
        raise DataError(
            f"Expected a JSON array in {path}, got {type(raw).__name__}",
            source="languoids.json",
        )

    result = {}
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        iso3 = (entry.get("iso639_3") or entry.get("iso") or "").lower()
        if not iso3 or len(iso3) != 3:
            continue
        result[iso3] = {
            "glottocode": entry.get("id", ""),
            "iso639_3": iso3,
            "macroarea": entry.get("macroarea"),
            "latitude": entry.get("latitude"),
            "longitude": entry.get("longitude"),
            "lineage": entry.get("lineage", []),
            "family": entry.get("family"),
            "status": entry.get("status", ""),
        }
    return result


def load_from_tree(tree_path: Path) -> dict:
    """Read the raw Glottolog tree (languoids/tree/)."""
    result = {}
    for root, _dirs, files in os.walk(tree_path):
        if "md.ini" not in files:
            continue
        md_path = Path(root) / "md.ini"
        glotto = {}
        glottocode = None
        iso3 = None
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("id ="):
                        glottocode = line.split("=", 1)[1].strip()
                    elif line.startswith("iso639-3 ="):
                        iso3 = line.split("=", 1)[1].strip().lower()
                    elif line.startswith("macroarea ="):
                        glotto["macroarea"] = line.split("=", 1)[1].strip()
                    elif line.startswith("latitude ="):
                        try:
                            glotto["latitude"] = float(
                                line.split("=", 1)[1].strip()
                            )
                        except ValueError:
                            glotto["latitude"] = None
                    elif line.startswith("longitude ="):
                        try:
                            glotto["longitude"] = float(
                                line.split("=", 1)[1].strip()
                            )
                        except ValueError:
                            glotto["longitude"] = None
                    elif line.startswith("family ="):
                        glotto["family"] = line.split("=", 1)[1].strip()
                    elif line.startswith("lineage ="):
                        lineage = line.split("=", 1)[1].strip()
                        glotto["lineage"] = [
                            x.strip() for x in lineage.split(",")
                        ]
        except OSError as e:
            log.warning("Could not read %s: %s", md_path, e)
            continue

        if iso3 and len(iso3) == 3:
            result[iso3] = {
                "glottocode": glottocode or "",
                "iso639_3": iso3,
                "macroarea": glotto.get("macroarea"),
                "latitude": glotto.get("latitude"),
                "longitude": glotto.get("longitude"),
                "lineage": glotto.get("lineage", []),
                "family": glotto.get("family"),
                "status": glotto.get("status", ""),
            }
    return result


# --- Wikidata SPARQL source ---

SPARQL_QUERY = """
SELECT ?iso3 ?glottocode ?familyLabel ?macroareaLabel ?coord ?statusLabel WHERE {
  ?lang wdt:P220 ?iso3 .
  OPTIONAL { ?lang wdt:P1394 ?glottocode . }
  OPTIONAL {
    ?lang wdt:P279 ?family .
    ?family rdfs:label ?familyLabel .
    FILTER(lang(?familyLabel) = "en")
  }
  OPTIONAL {
    ?lang wdt:P625 ?coord .
  }
  OPTIONAL {
    ?lang wdt:P1999 ?status .
    ?status rdfs:label ?statusLabel .
    FILTER(lang(?statusLabel) = "en")
  }
}
"""


def _parse_wikidata_rows(data: dict) -> dict:
    """Convert SPARQL JSON bindings into {iso3: {...}}."""
    rows = data.get("results", {}).get("bindings", [])
    if not isinstance(rows, list):
        raise DataError(
            "SPARQL response has no 'results.bindings' array.",
            source="wikidata",
        )

    result: dict = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        iso3 = row.get("iso3", {}).get("value", "").lower()
        if not iso3 or len(iso3) != 3:
            continue

        glottocode = row.get("glottocode", {}).get("value", "")
        family = row.get("familyLabel", {}).get("value", "")
        macroarea = row.get("macroareaLabel", {}).get("value", "")
        status = row.get("statusLabel", {}).get("value", "")
        coord = row.get("coord", {}).get("value", "")

        lat = lon = None
        if coord and "Point(" in coord:
            try:
                inner = coord.split("Point(", 1)[1].rstrip(")")
                lon_str, lat_str = inner.split()
                lat = float(lat_str)
                lon = float(lon_str)
            except (ValueError, IndexError):
                pass

        result[iso3] = {
            "glottocode": glottocode,
            "iso639_3": iso3,
            "macroarea": macroarea,
            "latitude": lat,
            "longitude": lon,
            "lineage": [],
            "family": family,
            "status": status,
        }

    return result


def _safe_http_to_operational(
    exc: SafeHTTPError,
    source: str,
) -> OperationalError:
    """Translate SafeHTTPError into a user-facing OperationalError."""
    retryable = (
        exc.kind in ("timeout", "transport")
        or (
            exc.status_code is not None
            and exc.status_code in (429, 500, 502, 503, 504)
        )
    )
    temporary = retryable

    return OperationalError(
        str(exc),
        source=source,
        kind=exc.kind,
        status_code=exc.status_code,
        temporary=temporary,
        retryable=retryable,
    )


def fetch_from_wikidata(config: dict) -> dict:
    """Fetch Glottolog metadata via Wikidata SPARQL.

    Endpoint, User-Agent and timeout are read from config.
    Returns {iso3: {glottocode, iso639_3, macroarea, latitude,
                     longitude, lineage, family, status}}.
    """
    sources = config.get("sources", {})
    wikidata = sources.get("wikidata", {})
    endpoint = wikidata.get("endpoint")
    if not endpoint:
        raise OperationalError(
            "Config: sources.wikidata.endpoint is missing. "
            "Check config.toml or GLFM_WIKIDATA_ENDPOINT.",
            source="wikidata",
            kind="invalid_response",
        )

    http = config.get("http", {})
    user_agent = http.get("user_agent", "GLFM/1.1.0")
    timeout = http.get("timeout", 60)

    log.info("Fetching Wikidata SPARQL: %s", endpoint)

    params = {"query": SPARQL_QUERY, "format": "json"}
    url = f"{endpoint}?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/sparql-results+json",
        },
    )

    t0 = time.time()
    try:
        with safe_urlopen(req, timeout=timeout) as resp:
            content_type = (
                resp.headers.get("Content-Type") or ""
            ).lower()
            if not content_type.startswith(
                "application/sparql-results+json"
            ):
                raise OperationalError(
                    f"Unexpected Content-Type from Wikidata: "
                    f"{content_type!r}",
                    source="wikidata",
                    kind="invalid_content_type",
                    status_code=resp.status,
                )
            raw = read_limited_response(
                resp, MAX_SPARQL_RESPONSE_BYTES
            )
    except SafeHTTPError as exc:
        raise _safe_http_to_operational(exc, source="wikidata") from exc

    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise DataError(
            f"Wikidata returned invalid JSON: {exc}",
            source="wikidata",
        ) from exc

    elapsed = time.time() - t0
    rows = data.get("results", {}).get("bindings", [])
    log.info(
        "Wikidata returned %d rows in %.1f seconds",
        len(rows),
        elapsed,
    )

    return _parse_wikidata_rows(data)


# --- Main ---

def build_glottolog(config: dict, force_wikidata: bool = False) -> dict:
    """Build glottolog.json data (does not write the file)."""
    data_dir = get_data_dir()
    languoids_json = data_dir / "languoids.json"
    languoids_tree = data_dir / "languoids" / "tree"

    if not force_wikidata and languoids_json.exists():
        log.info("Using local source: %s", languoids_json)
        return load_from_languoids_json(languoids_json)

    if not force_wikidata and languoids_tree.exists():
        log.info("Using local source: %s", languoids_tree)
        return load_from_tree(languoids_tree)

    log.info("No local source — fetching via Wikidata SPARQL")
    return fetch_from_wikidata(config)


def save_json(path: Path, data: dict) -> None:
    """Atomic JSON write."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                data, f, ensure_ascii=False, separators=(",", ":")
            )
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)
    except OSError as e:
        raise OperationalError(
            f"Could not write {path}: {e}",
            source="filesystem",
            kind="transport",
        ) from e


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build glottolog.json via Wikidata SPARQL.",
    )
    parser.add_argument(
        "--wikidata", action="store_true",
        help="Force Wikidata source (skip local data)",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output file (default: <data_dir>/glottolog.json)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    config = load_config()
    data_dir = get_data_dir()
    output = args.output or (data_dir / "glottolog.json")

    log.info("Data directory: %s", data_dir)

    try:
        data = build_glottolog(
            config, force_wikidata=args.wikidata
        )
    except OperationalError as exc:
        log.error("Source error: %s", exc)
        if exc.retryable:
            log.error("Error is temporary — try again later.")
        return 1
    except DataError as exc:
        log.error("Data error: %s", exc)
        return 1

    save_json(output, data)

    log.info(
        "Saved: %s (%d languages, %.1f kB)",
        output, len(data), output.stat().st_size / 1024,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
