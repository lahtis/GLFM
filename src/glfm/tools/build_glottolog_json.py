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
# Fetch the official Glottolog tree and languoid catalogue.
# Fallback source: Wikidata SPARQL. Local languoid files take precedence.
#
# Output: data/glottolog.json, keyed by ISO 639-3 code (e.g. "fin").
# Glottocode is a field, not a key.
#
# Wikidata endpoint, User-Agent and timeout are read from config.
# All outbound HTTP goes through glfm.utils.safe_http (vendored from SHL).
#

import argparse
import csv
import io
import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
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
MAX_GLOTTOLOG_TREE_BYTES = 5 * 1024 * 1024
MAX_GLOTTOLOG_CSV_ARCHIVE_BYTES = 5 * 1024 * 1024
MAX_GLOTTOLOG_CSV_BYTES = 20 * 1024 * 1024


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
            "lineage_names": entry.get("lineage_names", []),
            "family": entry.get("family"),
            "status": entry.get("status", ""),
        }
    return result


def load_from_tree(tree_path: Path) -> dict:
    """Read the raw Glottolog tree (languoids/tree/)."""
    nodes = {}
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
                    elif line.startswith("name ="):
                        glotto["name"] = line.split("=", 1)[1].strip()
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

        if glottocode:
            nodes[glottocode] = {
                **glotto,
                "glottocode": glottocode,
                "iso639_3": iso3,
                # md.ini lineage is ordered from the top-level family down.
                "lineage": list(reversed(glotto.get("lineage", []))),
            }

    result = {}
    for node in nodes.values():
        iso3 = node["iso639_3"]
        if not iso3 or len(iso3) != 3:
            continue
        lineage = [code for code in node.get("lineage", []) if code in nodes]
        names = [nodes[code].get("name", "") for code in lineage]
        result[iso3] = {
            "glottocode": node["glottocode"],
            "iso639_3": iso3,
            "macroarea": node.get("macroarea"),
            "latitude": node.get("latitude"),
            "longitude": node.get("longitude"),
            "lineage": lineage,
            "lineage_names": names,
            "family": names[-1] if names else node.get("family"),
            "status": node.get("status", ""),
        }
    return result


def _read_glottolog_csv(archive: bytes) -> dict[str, dict]:
    """Read the small official languoid CSV ZIP keyed by Glottocode."""
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            files = [name for name in zf.namelist() if name.lower().endswith(".csv")]
            if len(files) != 1:
                raise DataError(
                    "Glottolog ZIP must contain exactly one CSV file",
                    source="glottolog",
                )
            info = zf.getinfo(files[0])
            if info.file_size > MAX_GLOTTOLOG_CSV_BYTES:
                raise DataError("Glottolog CSV exceeds size limit", source="glottolog")
            text = zf.read(info).decode("utf-8-sig")
    except DataError:
        raise
    except (zipfile.BadZipFile, UnicodeDecodeError, OSError) as exc:
        raise DataError(f"Invalid Glottolog CSV ZIP: {exc}", source="glottolog") from exc

    result = {}
    for row in csv.DictReader(io.StringIO(text)):
        normalized = {str(key).casefold(): value for key, value in row.items()}
        code = (normalized.get("glottocode") or normalized.get("id") or "").strip()
        if not code:
            continue
        result[code] = {
            "iso3": (normalized.get("iso639p3code") or "").strip().lower(),
            "macroarea": (normalized.get("macroarea") or "").strip(),
            "latitude": normalized.get("latitude") or None,
            "longitude": normalized.get("longitude") or None,
        }
    return result


def _parse_newick_label(label: str) -> dict:
    """Extract a languoid name, Glottocode, and optional ISO code."""
    match = re.search(r"\[([a-z0-9]{4}[0-9]{4})\](?:\[([a-z]{3})\])?", label)
    if not match:
        return {"name": label.strip(), "glottocode": "", "iso3": ""}
    return {
        "name": label[:match.start()].strip(),
        "glottocode": match.group(1),
        "iso3": match.group(2) or "",
    }


def load_from_newick(text: str, metadata: dict[str, dict] | None = None) -> dict:
    """Parse Glottolog's labelled tree file into ISO-keyed lineage records."""
    metadata = metadata or {}
    result = {}

    def parse_tree(tree_text: str) -> dict:
        index = 0

        def skip_space() -> None:
            nonlocal index
            while index < len(tree_text) and tree_text[index].isspace():
                index += 1

        def read_label() -> str:
            nonlocal index
            skip_space()
            if index < len(tree_text) and tree_text[index] == "'":
                index += 1
                chars = []
                while index < len(tree_text):
                    char = tree_text[index]
                    index += 1
                    if char == "'":
                        if index < len(tree_text) and tree_text[index] == "'":
                            chars.append("'")
                            index += 1
                        else:
                            break
                    else:
                        chars.append(char)
                return "".join(chars)
            start = index
            while index < len(tree_text) and tree_text[index] not in ",():;":
                index += 1
            return tree_text[start:index].strip()

        def skip_length() -> None:
            nonlocal index
            skip_space()
            if index < len(tree_text) and tree_text[index] == ":":
                index += 1
                while index < len(tree_text) and tree_text[index] not in ",);":
                    index += 1

        def subtree() -> dict:
            nonlocal index
            skip_space()
            children = []
            if index < len(tree_text) and tree_text[index] == "(":
                index += 1
                while True:
                    children.append(subtree())
                    skip_space()
                    if index >= len(tree_text):
                        break
                    if tree_text[index] == ",":
                        index += 1
                        continue
                    if tree_text[index] == ")":
                        index += 1
                        break
                    raise ValueError("Invalid Glottolog Newick structure")
            label = read_label()
            skip_length()
            return {"label": label, "children": children}

        node = subtree()
        skip_space()
        if index < len(tree_text) and tree_text[index] != ";":
            raise ValueError("Trailing data in Glottolog Newick tree")
        return node

    def visit(node: dict, ancestors: list[dict]) -> None:
        parsed = _parse_newick_label(node["label"])
        next_ancestors = ancestors
        if parsed["glottocode"]:
            code = parsed["glottocode"]
            if parsed["iso3"]:
                parents = [item for item in ancestors if item["glottocode"]]
                lineage = [item["glottocode"] for item in reversed(parents)]
                names = [item["name"] for item in reversed(parents)]
                details = metadata.get(code, {})
                result[parsed["iso3"]] = {
                    "glottocode": code,
                    "iso639_3": parsed["iso3"],
                    "family": names[-1] if names else "",
                    "macroarea": details.get("macroarea", ""),
                    "latitude": details.get("latitude"),
                    "longitude": details.get("longitude"),
                    "lineage": lineage,
                    "lineage_names": names,
                    "status": "",
                }
            next_ancestors = [*ancestors, parsed]
        for child in node["children"]:
            visit(child, next_ancestors)

    try:
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            visit(parse_tree(line), [])
    except (ValueError, RecursionError) as exc:
        raise DataError(f"Invalid Glottolog Newick tree: {exc}", source="glottolog") from exc
    if not result:
        raise DataError("Glottolog tree contains no ISO-coded languages", source="glottolog")
    return result


def fetch_from_glottolog(config: dict) -> dict:
    """Fetch the compact official Glottolog tree and languoid catalogue."""
    source = config.get("sources", {}).get("glottolog", {})
    tree_url = source.get("tree_url")
    csv_url = source.get("csv_url")
    if not tree_url or not csv_url:
        raise OperationalError(
            "Config: sources.glottolog.tree_url or csv_url is missing.",
            source="glottolog",
            kind="invalid_response",
        )
    timeout = config.get("http", {}).get("timeout", 60)

    def fetch(url: str, max_bytes: int) -> bytes:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": config.get("http", {}).get("user_agent", "GLFM")},
        )
        try:
            with safe_urlopen(req, timeout=timeout) as resp:
                return read_limited_response(resp, max_bytes)
        except SafeHTTPError as exc:
            raise _safe_http_to_operational(exc, source="glottolog") from exc

    tree = fetch(tree_url, MAX_GLOTTOLOG_TREE_BYTES).decode("utf-8-sig")
    csv_archive = fetch(csv_url, MAX_GLOTTOLOG_CSV_ARCHIVE_BYTES)
    return load_from_newick(tree, _read_glottolog_csv(csv_archive))


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

def build_glottolog(
    config: dict,
    force_wikidata: bool = False,
    *,
    with_source: bool = False,
) -> dict | tuple[dict, dict]:
    """Build Glottolog metadata, optionally returning source provenance."""
    data_dir = get_data_dir()
    languoids_json = data_dir / "languoids.json"
    languoids_tree = data_dir / "languoids" / "tree"

    def result(data: dict, source: str) -> dict | tuple[dict, dict]:
        provenance = {
            "source": source,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "record_count": len(data),
            "lineage_count": sum(
                bool(info.get("lineage"))
                for info in data.values()
                if isinstance(info, dict)
            ),
        }
        return (data, provenance) if with_source else data

    if force_wikidata:
        return result(fetch_from_wikidata(config), "wikidata_forced")

    if languoids_json.exists():
        log.info("Using local source: %s", languoids_json)
        return result(
            load_from_languoids_json(languoids_json),
            "local_languoids_json",
        )

    if languoids_tree.exists():
        log.info("Using local source: %s", languoids_tree)
        return result(load_from_tree(languoids_tree), "local_languoids_tree")

    try:
        log.info("No local source — fetching official Glottolog tree and catalogue")
        data = fetch_from_glottolog(config)
        log.info("Glottolog tree contains %d ISO-coded languages", len(data))
        return result(data, "glottolog_official")
    except (OperationalError, DataError) as exc:
        log.warning("Glottolog catalogue unavailable (%s); using Wikidata", exc)
        return result(fetch_from_wikidata(config), "wikidata_fallback")


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
        description=(
            "Build glottolog.json from Glottolog, with a Wikidata fallback."
        ),
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
        data, provenance = build_glottolog(
            config,
            force_wikidata=args.wikidata,
            with_source=True,
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
    provenance_path = output.with_name("glottolog_source.json")
    save_json(provenance_path, provenance)
    log.info(
        "Source audit: %s (%d records; %d with lineage)",
        provenance["source"],
        provenance["record_count"],
        provenance["lineage_count"],
    )

    log.info(
        "Saved: %s (%d languages, %.1f kB)",
        output, len(data), output.stat().st_size / 1024,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
