#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.0.7
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
# Download the Wiktextract dump (~5-10 GB) to the cache.
# Usage:
#     python3 -m glfm.tools.download_wiktextract
#     python3 -m glfm.tools.download_wiktextract --url <url>
#     python3 -m glfm.tools.download_wiktextract --force
#

import argparse
import hashlib
import logging
import os
import sys
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)


def download_wiktextract(
    url: str,
    dest: Path,
    timeout: int = 3600,
    force: bool = False,
    chunk_size: int = 1024 * 1024,  # 1 MB
) -> Path:
    """
    Stream-download the Wiktextract dump to `dest`.

    Uses chunked streaming (1 MB) to avoid loading 5-10 GB into memory.
    Shows progress every 100 MB.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and not force:
        log.info("Wiktextract dump already exists: %s (%.1f GB)",
                 dest, dest.stat().st_size / 1e9)
        return dest

    log.info("Downloading: %s", url)
    log.info("Destination: %s", dest)

    tmp = dest.with_suffix(dest.suffix + ".tmp")
    sha256 = hashlib.sha256()
    downloaded = 0
    last_log = 0

    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            total = resp.headers.get("Content-Length")
            total = int(total) if total else None

            with open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    sha256.update(chunk)
                    downloaded += len(chunk)

                    # Log every 100 MB
                    if downloaded - last_log >= 100 * 1024 * 1024:
                        if total:
                            pct = downloaded / total * 100
                            log.info("  %.1f GB / %.1f GB (%.1f%%)",
                                     downloaded / 1e9, total / 1e9, pct)
                        else:
                            log.info("  %.1f GB", downloaded / 1e9)
                        last_log = downloaded

                f.flush()
                os.fsync(f.fileno())

        tmp.replace(dest)
        log.info("Downloaded: %s (%.1f GB)", dest, downloaded / 1e9)
        log.info("SHA256: %s", sha256.hexdigest())
        return dest

    except Exception as e:
        if tmp.exists():
            tmp.unlink()
        raise RuntimeError(f"Download failed: {e}") from e


def main():
    from glfm.config import load_config
    from glfm.paths import get_data_dir

    config = load_config()
    src_cfg = config["sources"].get("wiktextract", {})

    default_url = src_cfg.get("url", "")
    default_filename = src_cfg.get("filename", "raw-wiktextract-data.jsonl.gz")
    default_timeout = src_cfg.get("timeout", 3600)

    parser = argparse.ArgumentParser(
        description="Download the Wiktextract dump (~5-10 GB).",
    )
    parser.add_argument(
        "--url", default=default_url,
        help=f"Download URL (default: {default_url or 'not configured'})",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help=f"Output file (default: {get_data_dir() / default_filename})",
    )
    parser.add_argument(
        "--timeout", type=int, default=default_timeout,
        help=f"HTTP timeout in seconds (default: {default_timeout})",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force re-download",
    )
    args = parser.parse_args()

    if not args.url:
        log.error(
            "Wiktextract URL missing. Set it in config.toml:\n"
            "  [sources.wiktextract]\n"
            "  url = \"https://...\""
        )
        return 1

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    dest = args.output or (get_data_dir() / default_filename)

    try:
        download_wiktextract(
            args.url, dest,
            timeout=args.timeout,
            force=args.force,
        )
    except RuntimeError as e:
        log.error("%s", e)
        return 1

    print()
    print(f"Wiktextract dump: {dest}")
    print(f"Size: {dest.stat().st_size / 1e9:.1f} GB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
