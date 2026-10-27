#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.0.5
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Ensure src/ is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from glfm.paths import get_data_dir

log = logging.getLogger(__name__)

DEFAULT_INPUT = get_data_dir() / "unified_languages.json"
DEFAULT_OUTPUT = get_data_dir() / "validation" / "fallback_graph.dot"


def visualize_fallbacks(data: dict, output: Path) -> dict:
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
            roots += 1
            continue

        lines.append(f'  "{lang_id}" -> "{fb}";')
        edges += 1
        nodes += 1

    lines.append("}")

    if edges == 0:
        log.warning(
            "Fallback graph has no edges (%d roots, 0 edges). "
            "File not written.",
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
        description="Generate Graphviz DOT file from fallback chains.",
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if not args.input.exists():
        raise SystemExit(
            f"Input missing: {args.input}\n"
            f"Run first: python3 -m glfm.build_unified"
        )

    log.info("Reading: %s", args.input)
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    stats = visualize_fallbacks(data, args.output)

    if not stats["written"]:
        print()
        print(f"Fallback graph not written: 0 edges, {stats['roots']} roots.")
        print("This is normal if wiktionary_languages.json is missing")
        print("(all languages have fallback = themselves).")
        return 0

    print(f"Fallback graph written to: {args.output}")
    print(f"  Nodes:  {stats['nodes']}")
    print(f"  Edges:  {stats['edges']}")
    print(f"  Roots:  {stats['roots']}")
    print()
    print("Render with:")
    print(f"  dot -Tpng {args.output} -o fallback_graph.png")
    print(f"  dot -Tsvg {args.output} -o fallback_graph.svg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
