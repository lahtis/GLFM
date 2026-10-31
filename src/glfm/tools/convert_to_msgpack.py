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
# Convert a JSON file to MessagePack.
#
# NOTE: MessagePack is not shareable with other languages without a
# separate decoder — use .json.gz if you share data externally.
#
# Requires (data extras): msgpack
#     pip install -e ".[data]"
#
# msgpack is NOT a runtime dependency — it is only needed when this
# module is actually run. The import is therefore done lazily inside
# the function that needs it.
#

import argparse
import json
import logging
import os
from pathlib import Path

from glfm.errors import DataError, OperationalError
from glfm.paths import get_data_dir

log = logging.getLogger(__name__)


def _require_msgpack():
    """Import msgpack or raise a clear OperationalError."""
    try:
        import msgpack
        return msgpack
    except ImportError as e:
        raise OperationalError(
            f"msgpack is required for MessagePack conversion. "
            f"Install with: pip install -e \".[data]\" ({e})",
            source="msgpack",
            kind="invalid_response",
        ) from e


def convert_json_to_msgpack(
    input_path: Path,
    output_path: Path,
) -> dict:
    """Read a JSON file and write it in MessagePack format.

    Returns a dict with file sizes in bytes.
    """
    msgpack = _require_msgpack()

    if not input_path.exists():
        raise OperationalError(
            f"Input missing: {input_path}. "
            f"Run first: python3 -m glfm.tools.build_consumer_dataset",
            source="filesystem",
            kind="transport",
        )

    log.info("Reading: %s", input_path)
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise DataError(
            f"Invalid JSON in {input_path}: {e}",
            source="unified_languages.json",
        ) from e
    except OSError as e:
        raise OperationalError(
            f"Could not read {input_path}: {e}",
            source="filesystem",
            kind="transport",
        ) from e

    log.info("Packing MessagePack: %s", output_path)
    try:
        packed_bytes = msgpack.packb(data, use_bin_type=True)
    except (TypeError, ValueError) as e:
        raise DataError(
            f"Could not pack data as MessagePack: {e}",
            source="unified_languages.json",
        ) from e

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = output_path.with_suffix(output_path.suffix + ".tmp")
        with open(tmp, "wb") as f:
            f.write(packed_bytes)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(output_path)
    except OSError as e:
        raise OperationalError(
            f"Could not write {output_path}: {e}",
            source="filesystem",
            kind="transport",
        ) from e

    return {
        "input_size": input_path.stat().st_size,
        "output_size": output_path.stat().st_size,
    }


def main() -> int:
    data_root = get_data_dir()
    default_input = data_root / "unified" / "languages_top20.json"
    default_output = data_root / "unified" / "languages_top20.msgpack"

    parser = argparse.ArgumentParser(
        description="Convert JSON to MessagePack.",
    )
    parser.add_argument(
        "--input", type=Path, default=default_input,
        help=f"Input (default: {default_input})",
    )
    parser.add_argument(
        "--output", type=Path, default=default_output,
        help=f"Output (default: {default_output})",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        r = convert_json_to_msgpack(args.input, args.output)
    except OperationalError as exc:
        log.error("Source error: %s", exc)
        if exc.retryable:
            log.error("Error is temporary — try again later.")
        return 1
    except DataError as exc:
        log.error("Data error: %s", exc)
        return 1

    in_mb = r["input_size"] / (1024 * 1024)
    out_mb = r["output_size"] / (1024 * 1024)
    reduction = (1 - out_mb / in_mb) * 100 if in_mb > 0 else 0

    print()
    print("--- COMPRESSION TEST RESULTS ---")
    print(f"JSON file size:        {in_mb:.2f} MB")
    print(f"MessagePack file size: {out_mb:.2f} MB")
    print(f"Size reduction:        {reduction:.1f} %")
    print()
    print(f"File: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
