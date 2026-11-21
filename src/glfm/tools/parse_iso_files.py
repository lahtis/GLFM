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
# Parse ISO 639-1/2/3/5 source files and return a structured dict.
# Used by generate_iso_files.py.
#

import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

from glfm.errors import DataError, OperationalError

log = logging.getLogger(__name__)


def _read_lines(path: Path):
    """Yield non-empty lines from a file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if line.strip():
                    yield line
    except OSError as e:
        raise OperationalError(
            f"Could not read {path}: {e}",
            source="filesystem",
            kind="transport",
        ) from e


def parse_iso639_3(
    path: Path,
) -> tuple[Dict, Dict, Dict]:
    """Parse iso-639-3.tab.

    Columns: Id, Part2B, Part2T, Part1, Scope, Language_Type, Ref_Name
    Returns (iso1, iso2, iso3) dicts.
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
            log.debug(
                "Skipping line: too few columns: %r", line[:50]
            )
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

    log.info(
        "ISO 639-3: %d languages, 639-1: %d, 639-2: %d",
        len(iso3), len(iso1), len(iso2),
    )
    return iso1, iso2, iso3


def parse_iso639_3_names(path: Path) -> Dict[str, list]:
    """Parse iso-639-3_Name_Index.tab.

    Columns: Id, Print_Name, Inverted_Name
    Returns {iso3: [name1, name2, ...]}.
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
    log.info(
        "ISO 639-3 names: %d languages, %d names total",
        len(result), sum(len(v) for v in result.values()),
    )
    return result


def parse_iso639_3_macrolanguages(path: Path) -> Dict[str, list]:
    """Parse iso-639-3_macrolanguages.tab.

    Columns: M_Id, I_Id, I_Status
    Returns {macro: [individual, ...]}.
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

    log.info(
        "ISO 639-3 macrolanguages: %d macrolanguages", len(macros)
    )
    return macros


def _normalized_header(value: str) -> str:
    return "".join(ch.lower() for ch in value.lstrip("\ufeff") if ch.isalnum())


def parse_iso639_5_tsv(path: Path) -> Dict[str, Dict[str, str]]:
    """Parse the Library of Congress ISO 639-5 tab-delimited code list."""
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            headers = {
                _normalized_header(name): name
                for name in (reader.fieldnames or [])
                if name
            }
            code_key = next(
                (headers[key] for key in ("code", "iso6395", "id") if key in headers),
                None,
            )
            name_key = next(
                (
                    headers[key]
                    for key in ("labelenglish", "englishname", "name", "label")
                    if key in headers
                ),
                None,
            )
            uri_key = headers.get("uri")
            hierarchy_key = next(
                (value for key, value in headers.items() if "hierarchy" in key),
                None,
            )
            if not name_key or (not code_key and not uri_key):
                raise DataError(
                    "ISO 639-5 TSV is missing code or English-label columns.",
                    source="iso_639_5",
                )

            iso5: Dict[str, Dict[str, str]] = {}
            for row in reader:
                code = (row.get(code_key) or "").strip().lower() if code_key else ""
                if not code and uri_key:
                    uri = (row.get(uri_key) or "").strip().rstrip("/")
                    code = uri.rsplit("/", 1)[-1].lower()
                name = (row.get(name_key) or "").strip()
                if len(code) != 3 or not code.isalpha() or not name:
                    continue
                record = {"name": name}
                if hierarchy_key:
                    hierarchy = (row.get(hierarchy_key) or "").strip()
                    if hierarchy:
                        record["hierarchy"] = hierarchy
                iso5[code] = record
    except DataError:
        raise
    except (OSError, UnicodeError, csv.Error) as e:
        raise OperationalError(
            f"Could not parse ISO 639-5 TSV {path}: {e}",
            source="iso_639_5",
            kind="invalid_response",
        ) from e

    if not iso5:
        raise DataError(
            "ISO 639-5 TSV contained no valid code rows.",
            source="iso_639_5",
        )
    log.info("ISO 639-5: %d language families and groups", len(iso5))
    return iso5


def parse_all_iso_files(
    iso639_3_path: Path,
    name_index_path: Path,
    macrolanguages_path: Path,
    iso639_5_path: Path,
) -> Dict[str, Any]:
    """Parse all ISO sources and return a combined dict."""
    for p in (iso639_3_path, name_index_path, macrolanguages_path):
        if not Path(p).exists():
            raise OperationalError(
                f"Source file missing: {p}",
                source="filesystem",
                kind="transport",
            )

    iso1, iso2, iso3 = parse_iso639_3(Path(iso639_3_path))
    names = parse_iso639_3_names(Path(name_index_path))
    macros = parse_iso639_3_macrolanguages(Path(macrolanguages_path))

    iso5: Dict[str, Dict[str, str]] = {}
    if Path(iso639_5_path).exists():
        iso5 = parse_iso639_5_tsv(Path(iso639_5_path))
    else:
        log.warning("ISO 639-5 TSV missing: %s", iso639_5_path)

    return {
        "iso639_1": iso1,
        "iso639_2": iso2,
        "iso639_3": iso3,
        "iso639_3_names": names,
        "iso639_3_macrolanguages": macros,
        "iso639_5": iso5,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse ISO 639 source files to JSON.",
    )
    parser.add_argument("iso639_3", type=Path, help="iso-639-3.tab")
    parser.add_argument(
        "names", type=Path, help="iso-639-3_Name_Index.tab"
    )
    parser.add_argument(
        "macros", type=Path, help="iso-639-3_macrolanguages.tab"
    )
    parser.add_argument(
        "iso639_5", type=Path, help="iso639-5.tsv"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        data = parse_all_iso_files(
            args.iso639_3, args.names, args.macros, args.iso639_5,
        )
    except OperationalError as exc:
        log.error("Source error: %s", exc)
        if exc.retryable:
            log.error("Error is temporary — try again later.")
        return 1
    except DataError as exc:
        log.error("Data error: %s", exc)
        return 1

    try:
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
        print()
    except (OSError, ValueError) as exc:
        log.error("Could not write output: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
