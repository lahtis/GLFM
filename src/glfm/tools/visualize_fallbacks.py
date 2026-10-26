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
# Generoi Graphviz DOT -tiedoston fallback-ketjuista.
# HUOM: Vaatii graphviz-paketin vain renderöintiin (dot-komento),
# ei tämä skripti itsessään.
#
# Jos fallback-graafissa ei ole kaaria (kaikki kielet ovat juuria),
# tiedostoa EI kirjoiteta – se olisi 7927 riviä pelkkiä solmuja.
#

import argparse
import json
import logging
import os
from pathlib import Path

from glfm.paths import get_data_dir, get_output_dir

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = get_output_dir() / "unified" / "unified_languages.json"
DEFAULT_OUTPUT = get_output_dir() / "validation" / "fallback_graph.dot"


def visualize_fallbacks(data: dict, output: Path) -> dict:
    """
    Kirjoittaa Graphviz DOT -tiedoston fallback-ketjuista.

    Jos kaaria on 0 (kaikki kielet ovat juuria), tiedostoa ei kirjoiteta.

    Palauttaa tilastot:
        {"nodes": N, "edges": M, "roots": K, "written": bool}
    """
    lines = [
        "digraph Fallbacks {",
        "  rankdir=LR;",
        '  node [shape=box, fontname="Arial"];',
    ]

    nodes = 0
    edges = 0
    roots = 0

    for lang_id, info in data.items():
        if not isinstance(info, dict):
            continue

        fb = info.get("fallback")
        if not fb:
            continue

        if fb == lang_id:
            # Juurikieli (fallback = itsensä) – ei lisätä graafiin
            roots += 1
            continue

        # Normaali fallback-reuna
        lines.append(f'  "{lang_id}" -> "{fb}";')
        edges += 1
        nodes += 1

    lines.append("}")

    # Jos ei kaaria, älä kirjoita tiedostoa
    if edges == 0:
        log.warning(
            "Fallback-graafissa ei ole kaaria (%d juurta, 0 kaarta). "
            "Tiedostoa ei kirjoiteta.",
            roots,
        )
        return {"nodes": 0, "edges": 0, "roots": roots, "written": False}

    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(output)

    return {"nodes": nodes, "edges": edges, "roots": roots, "written": True}


def main():
    parser = argparse.ArgumentParser(
        description="Generoi Graphviz DOT -tiedosto fallback-ketjuista.",
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_INPUT,
        help=f"Syöte (oletus: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help=f"Tuloste (oletus: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if not args.input.exists():
        raise SystemExit(
            f"Syöte puuttuu: {args.input}\n"
            f"Aja ensin: python3 build_unified.py"
        )

    log.info("Luetaan: %s", args.input)
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    stats = visualize_fallbacks(data, args.output)

    if not stats["written"]:
        print()
        print(f"Fallback-graafia ei kirjoitettu: 0 kaarta, {stats['roots']} juurta.")
        print("Tämä on normaalia, jos wiktionary_languages.json puuttuu")
        print("(kaikki kielet ovat fallback = itsensä).")
        return 0

    print(f"Fallback graph written to: {args.output}")
    print(f"  Solmuja: {stats['nodes']}")
    print(f"  Kaaria:  {stats['edges']}")
    print(f"  Juuria:  {stats['roots']}")
    print()
    print("Renderöi komennolla:")
    print(f"  dot -Tpng {args.output} -o fallback_graph.png")
    print(f"  dot -Tsvg {args.output} -o fallback_graph.svg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
