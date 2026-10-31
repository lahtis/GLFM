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
# NOTE: This script produces .json files (data/iso_639_*.json).
# load_iso_639.py reads .py modules (data/iso_639_*.py).
# These are NOT the same thing. If you don't need the .json files,
# do not run this script.
#
# All outbound HTTP goes through glfm.utils.safe_http (vendored from SHL).
#

import argparse
import csv
import json
import logging
import os
import urllib.request
from pathlib import Path

from glfm.errors import DataError, OperationalError
from glfm.paths import get_data_dir
from glfm.utils.safe_http import safe_urlopen
from glfm.utils.safe_http_common import (
    SafeHTTPError,
    read_limited_response,
)

log = logging.getLogger(__name__)

# Upper bound per download (safety net against runaway responses).
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

# Fallback for ISO 639-3 (SIL occasionally blocks requests).
ISO_639_3_FALLBACK = (
    "https://raw.githubusercontent.com/haliaeetus/iso-639/"
    "master/data/iso-639-3.tab"
)


def _safe_http_to_operational(
    exc: SafeHTTPError,
    source: str,
) -> OperationalError:
    """Translate SafeHTTPError into a user-facing OperationalError."""
    retryable = (
        exc.kind in ("timeout", "transport")
        or (
            exc.status_code is not None
            and exc.status_code in (429, 500, 502, 503, 504)
        )
    )
    return OperationalError(
        str(exc),
        source=source,
        kind=exc.kind,
        status_code=exc.status_code,
        temporary=retryable,
        retryable=retryable,
    )


def _fetch_bytes(
    url: str,
    user_agent: str,
    timeout: int,
    source: str,
) -> bytes:
    """Fetch a URL via safe_urlopen and return its bytes."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent},
    )
    try:
        with safe_urlopen(req, timeout=timeout) as resp:
            return read_limited_response(resp, MAX_DOWNLOAD_BYTES)
    except SafeHTTPError as exc:
        raise _safe_http_to_operational(exc, source=source) from exc


def download(
    url: str,
    path: Path,
    user_agent: str,
    timeout: int = 60,
    source: str = "",
) -> None:
    """Download a file, with an ISO 639-3 fallback mirror."""
    log.info("Downloading: %s", url)

    try:
        data = _fetch_bytes(url, user_agent, timeout, source)
    except OperationalError as e:
        log.warning("Primary download failed: %s", e)
        if "iso-639-3.tab" not in url:
            raise

        log.info("Trying fallback mirror: %s", ISO_639_3_FALLBACK)
        data = _fetch_bytes(
            ISO_639_3_FALLBACK, user_agent, timeout, source
        )
        log.info("Downloaded from fallback: %s", path)

    try:
        path.write_bytes(data)
    except OSError as e:
        raise OperationalError(
            f"Could not write {path}: {e}",
            source="filesystem",
            kind="transport",
        ) from e

    log.info("Saved: %s (%.1f kB)", path, len(data) / 1024)


def _atomic_write_json(path: Path, data: dict) -> None:
    """Atomic JSON write with human-readable formatting."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                data, f,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)
    except OSError as e:
        raise OperationalError(
            f"Could not write {path}: {e}",
            source="filesystem",
            kind="transport",
        ) from e


def build_iso_639_3(
    data_root: Path,
    url: str,
    user_agent: str,
    timeout: int,
) -> None:
    """Build iso_639_3.json from SIL's .tab file."""
    tmp = data_root / "iso-639-3.tab"
    download(
        url, tmp, user_agent, timeout,
        source="iso_639_3",
    )

    iso3: dict = {}
    try:
        with open(tmp, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                code3 = (row.get("Id") or "").strip()
                if not code3:
                    continue

                iso2B = (
                    row.get("Part2_B") or row.get("Part2B") or ""
                ).strip()
                iso2T = (
                    row.get("Part2_T") or row.get("Part2T") or ""
                ).strip()
                iso1 = (row.get("Part1") or "").strip()

                iso3[code3] = {
                    "name": (row.get("Ref_Name") or "").strip(),
                    "iso639_3": code3,
                    "iso639_2B": iso2B,
                    "iso639_2T": iso2T,
                    "iso639_1": iso1,
                    "iso639_5": "",
                }
    except (OSError, csv.Error) as e:
        raise DataError(
            f"Could not parse {tmp}: {e}",
            source="iso_639_3",
        ) from e

    _atomic_write_json(data_root / "iso_639_3.json", iso3)
    log.info(
        "Built: %s (%d languages)",
        data_root / "iso_639_3.json", len(iso3),
    )


def build_iso_639_2(
    data_root: Path,
    url: str,
    user_agent: str,
    timeout: int,
) -> None:
    """Build iso_639_2.json from the Library of Congress list."""
    tmp = data_root / "iso-639-2.txt"
    download(
        url, tmp, user_agent, timeout,
        source="iso_639_2",
    )

    iso2: dict = {}
    try:
        with open(tmp, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) < 4:
                    continue

                code2B, code2T, code1, name = [
                    p.strip() for p in parts[:4]
                ]
                key = code2T or code2B
                if not key:
                    continue

                iso2[key] = {
                    "name": name,
                    "iso639_2B": code2B,
                    "iso639_2T": code2T,
                    "iso639_1": code1,
                    "iso639_3": "",
                }
    except OSError as e:
        raise DataError(
            f"Could not parse {tmp}: {e}",
            source="iso_639_2",
        ) from e

    _atomic_write_json(data_root / "iso_639_2.json", iso2)
    log.info(
        "Built: %s (%d languages)",
        data_root / "iso_639_2.json", len(iso2),
    )


def build_iso_639_1(
    data_root: Path,
    url: str,
    user_agent: str,
    timeout: int,
) -> None:
    """Build iso_639_1.json from the DataHub CSV."""
    tmp = data_root / "language-codes.csv"
    download(
        url, tmp, user_agent, timeout,
        source="iso_639_1",
    )

    iso1: dict = {}
    try:
        with open(tmp, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code1 = (
                    row.get("alpha2") or row.get("Alpha2")
                    or row.get("ISO639-1") or ""
                ).strip()
                if not code1:
                    continue

                code3 = (
                    row.get("alpha3-b") or row.get("alpha3")
                    or row.get("Alpha3") or row.get("ISO639-2B")
                    or row.get("ISO639-3") or ""
                ).strip()
                name = (
                    row.get("English") or row.get("Name")
                    or row.get("name") or ""
                ).strip()

                iso1[code1] = {
                    "name": name,
                    "iso639_1": code1,
                    "iso639_3": code3,
                }
    except (OSError, csv.Error) as e:
        raise DataError(
            f"Could not parse {tmp}: {e}",
            source="iso_639_1",
        ) from e

    _atomic_write_json(data_root / "iso_639_1.json", iso1)
    log.info(
        "Built: %s (%d languages)",
        data_root / "iso_639_1.json", len(iso1),
    )


def _read_source_url(config: dict, key: str) -> str:
    """Read a source URL from config, or raise OperationalError."""
    sources = config.get("sources", {})
    entry = sources.get(key, {})
    url = entry.get("url")
    if not url:
        raise OperationalError(
            f"Config: sources.{key}.url is missing. "
            f"Check config.toml or GLFM_ISO_{key.upper()}_URL.",
            source=key,
            kind="invalid_response",
        )
    return url


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download and build ISO 639 JSON files (redundant).",
    )
    parser.add_argument(
        "--skip-iso3", action="store_true", help="Skip ISO 639-3"
    )
    parser.add_argument(
        "--skip-iso2", action="store_true", help="Skip ISO 639-2"
    )
    parser.add_argument(
        "--skip-iso1", action="store_true", help="Skip ISO 639-1"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    from glfm.config import load_config

    config = load_config()
    http = config.get("http", {})
    user_agent = http.get(
        "user_agent", "GLFM/1.1.0 (https://codeberg.org/lahtis/GLFM)"
    )
    timeout = http.get("timeout", 60)

    data_root = get_data_dir()

    log.info("=== Building ISO 639 JSON files ===")
    try:
        if not args.skip_iso3:
            build_iso_639_3(
                data_root,
                _read_source_url(config, "iso_639_3"),
                user_agent,
                timeout,
            )
        if not args.skip_iso2:
            build_iso_639_2(
                data_root,
                _read_source_url(config, "iso_639_2"),
                user_agent,
                timeout,
            )
        if not args.skip_iso1:
            build_iso_639_1(
                data_root,
                _read_source_url(config, "iso_639_1"),
                user_agent,
                timeout,
            )
    except OperationalError as exc:
        log.error("Source error: %s", exc)
        if exc.retryable:
            log.error("Error is temporary — try again later.")
        return 1
    except DataError as exc:
        log.error("Data error: %s", exc)
        return 1

    log.info("=== Done ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
