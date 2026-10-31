#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# research.py — GLFM query tool
# Lukee joko consumer (top-20) tai research (top-100) -tietokantaa.
#

import argparse
import gzip
import json
import sys
from pathlib import Path

# --- Polut ---
CACHE = Path.home() / ".cache" / "glfm" / "data"

# Tier → tiedostonimi
TIER_FILES = {
    "consumer": "languages_top20.json.gz",
    "research": "unified_languages.json.gz",
}

DEFAULT_TIER = "research"


def load_database(tier: str) -> dict:
    """Lataa valitun tason tietokannan."""
    if tier not in TIER_FILES:
        raise SystemExit(f"Tuntematon tier: {tier}. Valinnat: {', '.join(TIER_FILES)}")

    path = CACHE / TIER_FILES[tier]
    if not path.exists():
        raise SystemExit(
            f"Tietokantaa ei löydy: {path}\n"
            f"Lataa se ensin: glfm download --tier {tier}"
        )

    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def hae_kieli(languages: dict, koodi: str) -> dict | None:
    """Hakee kielen tiedot kolmikirjaimisella ISO 639-3 -koodilla."""
    return languages.get(koodi.strip().lower())


def main():
    parser = argparse.ArgumentParser(
        description="Hae kielen tiedot GLFM-tietokannasta.",
    )
    parser.add_argument(
        "koodi",
        help="ISO 639-3 -koodi (esim. fin, eng, yok)",
    )
    parser.add_argument(
        "--tier", "-t",
        choices=list(TIER_FILES.keys()),
        default=DEFAULT_TIER,
        help=f"Tietokantataso (oletus: {DEFAULT_TIER})",
    )
    parser.add_argument(
        "--neighbors", "-n",
        type=int,
        default=None,
        help="Näytä vain N lähikieltä (oletus: kaikki)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Tulosta raaka JSON (ei muotoilua)",
    )
    args = parser.parse_args()

    languages = load_database(args.tier)
    tiedot = hae_kieli(languages, args.koodi)

    if tiedot is None:
        print(f"Kieltä '{args.koodi}' ei löytynyt tasolta '{args.tier}'.",
              file=sys.stderr)
        sys.exit(1)

    # Rajaa naapurit tarvittaessa
    if args.neighbors is not None and "nearest_languages" in tiedot:
        tiedot = dict(tiedot)  # kopio, ei muuta alkuperäistä
        tiedot["nearest_languages"] = tiedot["nearest_languages"][:args.neighbors]

    if args.json:
        print(json.dumps(tiedot, ensure_ascii=False, separators=(",", ":")))
    else:
        print(f"# {args.koodi} ({args.tier})")
        print(json.dumps(tiedot, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
