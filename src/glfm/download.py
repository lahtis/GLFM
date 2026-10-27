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
# Download a data package to ~/.cache/glfm/data/.
# Usage:
#     python3 -m glfm.download                    # consumer (558 kB)
#     python3 -m glfm.download --tier research    # research (1.4 MB)
#     python3 -m glfm.download --force
#

import argparse
import hashlib
import logging
import os
import sys
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

TIERS = ("consumer", "research")

# Filename for each tier (saved as-is, .gz)
TIER_FILENAMES = {
    "consumer": "languages_top20.json.gz",
    "research": "unified_languages.json.gz",
}


def download_data(force: bool = False, tier: str = "consumer") -> Path:
    """
    Download a data package to the cache (~/.cache/glfm/data/).

    The file is saved as-is (.json.gz) — callers decompress it into
    memory when needed.

    Args:
        force: force re-download even if data exists
        tier: "consumer" (558 kB) or "research" (1.4 MB)

    Returns:
        Path to the data directory
    """
    from glfm.config import load_config
    from glfm.paths import get_cache_dir

    if tier not in TIERS:
        raise ValueError(f"Unknown tier: {tier}. Choices: {TIERS}")

    config = load_config()
    cache = get_cache_dir() / "data"

    # Check if already downloaded
    marker = cache / f".downloaded_{tier}"
    if cache.exists() and marker.exists() and not force:
        log.info("Data (%s) already exists: %s", tier, cache)
        return cache

    # Get tier-specific config
    download_cfg = config["download"].get(tier)
    if not download_cfg:
        raise RuntimeError(
            f"Config: download.{tier} missing. Check config.toml."
        )

    # Try primary URL, then mirrors
    urls = [download_cfg["url"]]
    for name, url in download_cfg.get("mirrors", {}).items():
        if url != download_cfg["url"]:
            urls.append(url)

    data = None
    last_error = None

    for url in urls:
        try:
            log.info("Downloading (%s): %s", tier, url)
            with urllib.request.urlopen(
                url, timeout=download_cfg["timeout"]
            ) as resp:
                data = resp.read()
            log.info("Downloaded (%s): %.1f kB", tier, len(data) / 1024)
            break
        except Exception as e:
            log.warning("Download failed (%s): %s", url, e)
            last_error = e
            continue

    if data is None:
        raise RuntimeError(f"All downloads failed: {last_error}")

    # Verify hash
    if sha256 := download_cfg.get("sha256"):
        h = hashlib.sha256(data).hexdigest()
        if h != sha256:
            raise RuntimeError(f"SHA256 mismatch: {h} != {sha256}")

    # Save as-is (.json.gz) — do NOT extract, do NOT delete cache
    cache.mkdir(parents=True, exist_ok=True)

    filename = TIER_FILENAMES[tier]
    output = cache / filename
    tmp = output.with_suffix(output.suffix + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(output)

    # Mark as downloaded
    marker.touch()

    log.info("Done (%s): %s (%.1f kB)", tier, output, len(data) / 1024)
    return cache


def _data_size(path: Path) -> int:
    """Return the size of a directory in bytes."""
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def main():
    parser = argparse.ArgumentParser(
        description="Download GLFM data to ~/.cache/glfm/data/.",
    )
    parser.add_argument(
        "--tier", choices=TIERS, default="consumer",
        help="Data package: consumer (558 kB) or research (1.4 MB)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force re-download",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        path = download_data(force=args.force, tier=args.tier)
    except (RuntimeError, ValueError) as e:
        log.error("%s", e)
        return 1

    size_kt = _data_size(path) / 1024
    print()
    print(f"Data ({args.tier}): {path}")
    print(f"Size: {size_kt:.1f} kB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
