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
# research.py - GLFM query tool
# Reads either the consumer (top-20) or research (top-100) database.
#

import argparse
import gzip
import json
import logging
import sys
from pathlib import Path

from glfm.errors import OperationalError
from glfm.paths import get_data_dir

log = logging.getLogger(__name__)

# Tier -> filename
TIER_FILES = {
    "consumer": "languages_top20.json.gz",
    "research": "unified_languages.json.gz",
}

DEFAULT_TIER = "research"


def load_database(tier: str) -> dict:
    """Load the database for the given tier."""
    if tier not in TIER_FILES:
        raise OperationalError(
            f"Unknown tier: {tier}. Choices: {', '.join(TIER_FILES)}",
            source="research",
            kind="invalid_response",
        )

    path = get_data_dir() / TIER_FILES[tier]
    if not path.exists():
        raise OperationalError(
            f"Database not found: {path}. "
            f"Download it first: glfm download --tier {tier}",
            source="research",
            kind="transport",
        )

    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise OperationalError(
            f"Could not read {path}: {e}",
            source="research",
            kind="transport",
        ) from e


def lookup_language(languages: dict, code: str) -> dict | None:
    """Look up a language by three-letter ISO 639-3 code."""
    return languages.get(code.strip().lower())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query language data from the GLFM database.",
    )
    parser.add_argument(
        "code",
        help="ISO 639-3 code (e.g. fin, eng, yok)",
    )
    parser.add_argument(
        "--tier", "-t",
        choices=list(TIER_FILES.keys()),
        default=DEFAULT_TIER,
        help=f"Database tier (default: {DEFAULT_TIER})",
    )
    parser.add_argument(
        "--neighbors", "-n",
        type=int,
        default=None,
        help="Show only N nearest languages (default: all)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSON (no formatting)",
    )
    args = parser.parse_args()

    try:
        languages = load_database(args.tier)
    except OperationalError as exc:
        log.error("%s", exc)
        return 1

    tiedot = lookup_language(languages, args.code)

    if tiedot is None:
        print(
            f"Language '{args.code}' not found in tier '{args.tier}'.",
            file=sys.stderr,
        )
        return 1

    # Limit neighbors if requested
    if args.neighbors is not None and "nearest_languages" in tiedot:
        tiedot = dict(tiedot)  # copy, do not mutate original
        tiedot["nearest_languages"] = tiedot["nearest_languages"][
            :args.neighbors
        ]

    if args.json:
        print(
            json.dumps(
                tiedot, ensure_ascii=False, separators=(",", ":")
            )
        )
    else:
        print(f"# {args.code} ({args.tier})")
        print(json.dumps(tiedot, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )
    raise SystemExit(main())
