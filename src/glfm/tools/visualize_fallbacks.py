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

import argparse
import json
import logging
import os
from pathlib import Path

from glfm.errors import OperationalError
from glfm.paths import get_data_dir

log = logging.getLogger(__name__)


def _atomic_write_text(path: Path, content: str) -> None:
    """Atomic text write."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)
    except OSError as e:
        raise OperationalError(
            f"Could not write {path}: {e}",
            source="filesystem",
            kind="transport",
        ) from e


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
        return {
            "nodes": 0,
            "edges": 0,
            "roots": roots,
            "written": False,
        }

    _atomic_write_text(output, "\n".join(lines))

    return {
        "nodes": nodes,
        "edges": edges,
        "roots": roots,
        "written": True,
    }


def main() -> int:
    data_root = get_data_dir()
    default_input = data_root / "unified_languages.json"
    default_output = data_root / "validation" / "fallback_graph.dot"

    parser = argparse.ArgumentParser(
        description=(
            "Generate Graphviz DOT file from fallback chains."
        ),
    )
    parser.add_argument("--input", type=Path, default=default_input)
    parser.add_argument("--output", type=Path, default=default_output)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if not args.input.exists():
        log.error("Input missing: %s", args.input)
        log.error("Run first: python3 -m glfm.build_unified")
        return 1

    log.info("Reading: %s", args.input)
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        log.error("Invalid JSON in %s: %s", args.input, e)
        return 1
    except OSError as e:
        log.error("Could not read %s: %s", args.input, e)
        return 1

    if not isinstance(data, dict):
        log.error(
            "Expected a JSON object, got %s", type(data).__name__
        )
        return 1

    try:
        stats = visualize_fallbacks(data, args.output)
    except OperationalError as exc:
        log.error("%s", exc)
        return 1

    if not stats["written"]:
        print()
        print(
            f"Fallback graph not written: 0 edges, "
            f"{stats['roots']} roots."
        )
        print(
            "This is normal if wiktionary_languages.json is missing"
        )
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
