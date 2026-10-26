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
# Hakee Glottolog-metadatan Wikidata SPARQL:lla.
# Vaihtoehtoinen lähde: paikallinen languoids.json tai languoids/tree/.
#
# Tulos: data/glottolog.json, avaimena ISO 639-3 -koodi (esim. "fin").
# Glottocode on kenttänä, ei avaimena.
#
# Wikidata-endpoint, User-Agent ja timeout luetaan configista.
#

import argparse
import json
import logging
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _setup_imports() -> None:
    """Varmistaa että src/ on sys.path:ssä (kehitys)."""
    src = PROJECT_ROOT / "src"
    if src.exists() and str(src) not in sys.path:
        sys.path.insert(0, str(src))


_setup_imports()

from glfm.config import load_config
from glfm.paths import get_data_dir


# --- Paikalliset lähteet (jos olemassa) ---

def load_from_languoids_json(path: Path) -> dict:
    """Lukee paikallisen languoids.json-tiedoston."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    result = {}
    for entry in raw:
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
    """Lukee Glottologin raakapuun (languoids/tree/)."""
    result = {}
    for root, _dirs, files in os.walk(tree_path):
        if "md.ini" not in files:
            continue
        md_path = Path(root) / "md.ini"
        glotto = {}
        glottocode = None
        iso3 = None
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
                        glotto["latitude"] = float(line.split("=", 1)[1].strip())
                    except ValueError:
                        glotto["latitude"] = None
                elif line.startswith("longitude ="):
                    try:
                        glotto["longitude"] = float(line.split("=", 1)[1].strip())
                    except ValueError:
                        glotto["longitude"] = None
                elif line.startswith("family ="):
                    glotto["family"] = line.split("=", 1)[1].strip()
                elif line.startswith("lineage ="):
                    lineage = line.split("=", 1)[1].strip()
                    glotto["lineage"] = [x.strip() for x in lineage.split(",")]

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


# --- Wikidata SPARQL -lähde ---

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


def fetch_from_wikidata(config: dict) -> dict:
    """
    Hakee Glottolog-metadatan Wikidata SPARQL:lla.

    Endpoint, User-Agent ja timeout luetaan configista.
    Palauttaa {iso3: {glottocode, iso639_3, macroarea, latitude,
                       longitude, lineage, family, status}}
    """
    sources = config.get("sources", {})
    wikidata = sources.get("wikidata", {})
    endpoint = wikidata.get("endpoint")
    if not endpoint:
        raise RuntimeError(
            "Config: sources.wikidata.endpoint puuttuu. "
            "Tarkista config.toml tai GLFM_WIKIDATA_ENDPOINT."
        )

    http = config.get("http", {})
    user_agent = http.get("user_agent", "glfm/1.0.4")
    timeout = http.get("timeout", 60)

    log.info("Haetaan Wikidata SPARQL: %s", endpoint)

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
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError(
            f"Wikidata-kysely epäonnistui: {e}. "
            f"Yritä myöhemmin uudelleen tai käytä paikallista lähdettä."
        ) from e

    elapsed = time.time() - t0
    rows = data.get("results", {}).get("bindings", [])
    log.info("Wikidata palautti %d riviä %.1f sekunnissa", len(rows), elapsed)

    result: dict = {}
    for row in rows:
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


# --- Pääohjelma ---

def build_glottolog(config: dict, force_wikidata: bool = False) -> dict:
    """Rakentaa glottolog.json-datan (ei kirjoita tiedostoa)."""
    data_dir = get_data_dir()
    languoids_json = data_dir / "languoids.json"
    languoids_tree = data_dir / "languoids" / "tree"

    if not force_wikidata and languoids_json.exists():
        log.info("Käytetään paikallista lähdettä: %s", languoids_json)
        return load_from_languoids_json(languoids_json)

    if not force_wikidata and languoids_tree.exists():
        log.info("Käytetään paikallista lähdettä: %s", languoids_tree)
        return load_from_tree(languoids_tree)

    log.info("Ei paikallista lähdettä – haetaan Wikidata SPARQL:lla")
    return fetch_from_wikidata(config)


def save_json(path: Path, data: dict) -> None:
    """Atominen JSON-kirjoitus."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser(
        description="Rakenna glottolog.json Wikidata SPARQL:lla.",
    )
    parser.add_argument(
        "--wikidata", action="store_true",
        help="Pakota Wikidata-lähde (ohita paikallinen data)",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Tulostiedosto (oletus: <data_dir>/glottolog.json)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    config = load_config()
    data_dir = get_data_dir()

    output = args.output or (data_dir / "glottolog.json")

    log.info("Data-hakemisto: %s", data_dir)

    try:
        data = build_glottolog(config, force_wikidata=args.wikidata)
    except RuntimeError as e:
        log.error("%s", e)
        return 1

    save_json(output, data)

    log.info(
        "Tallennettu: %s (%d kieltä, %.1f kt)",
        output, len(data), output.stat().st_size / 1024,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
