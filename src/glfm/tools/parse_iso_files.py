#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.0.2
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
# Parsii ISO 639-1/2/3/5 -lähdetiedostot ja palauttaa jäsennellyn dictin.
# Käytetään generate_iso_files.py:stä.
#

import argparse
import json
import logging
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from glfm.paths import get_data_dir, get_output_dir
from typing import Any, Dict

log = logging.getLogger(__name__)

# ISO 639-3 .tab -otsikko
ISO3_HEADER = "Id\tPart2B\tPart2T\tPart1\tScope\tLanguage_Type\tRef_Name"

# ISO 639-5 SKOS -nimiavaruudet
SKOS_NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
}
RDF_ABOUT = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about"


def _read_lines(path: Path):
    """Lukee rivit tiedostosta, ohittaa tyhjät."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip():
                yield line


def parse_iso639_3(path: Path) -> tuple[Dict, Dict, Dict]:
    """
    Parsii iso-639-3.tab.

    Sarakkeet: Id, Part2B, Part2T, Part1, Scope, Language_Type, Ref_Name
    Palauttaa (iso1, iso2, iso3) -dictit.
    """
    iso3: Dict[str, Any] = {}
    iso1: Dict[str, str] = {}
    iso2: Dict[str, Dict[str, str]] = {}

    first = True
    for line in _read_lines(path):
        if first:
            first = False
            if line.startswith("Id\t"):
                continue

        parts = line.split("\t")
        if len(parts) < 7:
            log.debug("Ohitetaan rivi: liian vähän sarakkeita: %r", line[:50])
            continue

        parts = parts[:7]
        code3, part2b, part2t, part1, scope, ltype, name = parts

        iso3[code3] = {
            "name": name,
            "iso639_3": code3,
            "iso639_2B": part2b or "",
            "iso639_2T": part2t or "",
            "iso639_1": part1 or "",
            "scope": scope,
            "type": ltype,
        }

        if part1:
            iso1[part1] = code3

        if part2b or part2t:
            iso2[code3] = {
                "iso639_2B": part2b or "",
                "iso639_2T": part2t or "",
            }

    log.info("ISO 639-3: %d kieltä, 639-1: %d, 639-2: %d",
             len(iso3), len(iso1), len(iso2))
    return iso1, iso2, iso3


def parse_iso639_3_names(path: Path) -> Dict[str, list]:
    """
    Parsii iso-639-3_Name_Index.tab.

    Sarakkeet: Id, Print_Name, Inverted_Name
    Palauttaa {iso3: [nimi1, nimi2, ...]}.
    """
    names: Dict[str, set] = {}

    first = True
    for line in _read_lines(path):
        if first:
            first = False
            if line.startswith("Id\t"):
                continue

        parts = line.split("\t")
        if len(parts) < 3:
            continue

        code3, print_name, inverted_name = parts[:3]

        entry = names.setdefault(code3, set())
        if print_name.strip():
            entry.add(print_name.strip())
        if inverted_name.strip():
            entry.add(inverted_name.strip())

    result = {k: sorted(v) for k, v in names.items()}
    log.info("ISO 639-3 nimet: %d kieltä, %d nimeä yhteensä",
             len(result), sum(len(v) for v in result.values()))
    return result


def parse_iso639_3_macrolanguages(path: Path) -> Dict[str, list]:
    """
    Parsii iso-639-3_macrolanguages.tab.

    Sarakkeet: M_Id, I_Id, I_Status
    Palauttaa {makrokieli: [yksittäinen_kieli, ...]}.
    """
    macros: Dict[str, list] = {}

    first = True
    for line in _read_lines(path):
        if first:
            first = False
            if line.startswith("M_Id\t"):
                continue

        parts = line.split("\t")
        if len(parts) < 3:
            continue

        macro, individual, _status = parts[:3]
        macros.setdefault(macro, []).append(individual)

    log.info("ISO 639-3 makrokielet: %d makrokieltä", len(macros))
    return macros


def parse_iso639_5_rdf(path: Path) -> Dict[str, str]:
    """
    Parsii ISO 639-5 SKOS RDF -tiedoston.

    Palauttaa {koodi: nimi}.
    """
    iso5: Dict[str, str] = {}

    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        log.error("ISO 639-5 RDF ei ole kelvollinen XML: %s", e)
        return {}

    root = tree.getroot()

    for concept in root.findall("rdf:Description", SKOS_NS):
        about = concept.get(RDF_ABOUT)
        if not about:
            continue

        # Hyväksy vain ISO 639-5 -koodit
        if not about.startswith("http://id.loc.gov/vocabulary/iso639-5/"):
            continue

        code = about.rsplit("/", 1)[-1]
        label = concept.find("skos:prefLabel", SKOS_NS)
        if label is not None and label.text:
            iso5[code] = label.text

    log.info("ISO 639-5: %d kieliperhettä", len(iso5))
    return iso5


def parse_all_iso_files(
    iso639_3_path: Path,
    name_index_path: Path,
    macrolanguages_path: Path,
    iso639_5_path: Path,
) -> Dict[str, Any]:
    """
    Parsii kaikki ISO-lähteet ja palauttaa yhdistetyn dictin.
    """
    for p in (iso639_3_path, name_index_path, macrolanguages_path):
        if not Path(p).exists():
            raise FileNotFoundError(f"Lähdetiedosto puuttuu: {p}")

    iso1, iso2, iso3 = parse_iso639_3(Path(iso639_3_path))
    names = parse_iso639_3_names(Path(name_index_path))
    macros = parse_iso639_3_macrolanguages(Path(macrolanguages_path))

    iso5: Dict[str, str] = {}
    if Path(iso639_5_path).exists():
        iso5 = parse_iso639_5_rdf(Path(iso639_5_path))
    else:
        log.warning("ISO 639-5 RDF puuttuu: %s", iso639_5_path)

    return {
        "iso639_1": iso1,
        "iso639_2": iso2,
        "iso639_3": iso3,
        "iso639_3_names": names,
        "iso639_3_macrolanguages": macros,
        "iso639_5": iso5,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Parsii ISO 639 -lähdetiedostot JSON-muotoon.",
    )
    parser.add_argument("iso639_3", type=Path, help="iso-639-3.tab")
    parser.add_argument("names", type=Path, help="iso-639-3_Name_Index.tab")
    parser.add_argument("macros", type=Path, help="iso-639-3_macrolanguages.tab")
    parser.add_argument("iso639_5", type=Path, help="iso-639-5.skos.rdf")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    data = parse_all_iso_files(
        args.iso639_3, args.names, args.macros, args.iso639_5,
    )

    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
