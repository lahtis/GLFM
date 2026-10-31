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
# Fetch and read CLDR likelySubtags data.
# URL and version are read from config (glfm.config / config.toml / env).
#

import argparse
import gzip
import json
import logging
import urllib.request
from pathlib import Path

from glfm.config import load_config
from glfm.errors import DataError, OperationalError
from glfm.paths import get_data_dir
from glfm.utils.safe_http import safe_urlopen
from glfm.utils.safe_http_common import (
    SafeHTTPError,
    read_limited_response,
)

log = logging.getLogger(__name__)

# CLDR likelySubtags is small (<1 MB compressed).
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


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


def _get_cldr_config(config: dict) -> dict:
    """Return CLDR config from a loaded config dict."""
    cldr = config.get("sources", {}).get("cldr", {})
    if not cldr.get("url"):
        raise OperationalError(
            "Config: sources.cldr.url is missing. "
            "Check config.toml or GLFM_CLDR_URL.",
            source="cldr",
            kind="invalid_response",
        )
    http = config.get("http", {})
    return {
        "version": cldr.get("version", "unknown"),
        "url": cldr["url"],
        "user_agent": http["user_agent"],
        "timeout": http.get("timeout", 60),
    }


def _cldr_local_file() -> Path:
    """Return the CLDR file path (data/cldr/likelySubtags.json.gz)."""
    return get_data_dir() / "cldr" / "likelySubtags.json.gz"


def fetch_cldr_likely_subtags(
    config: dict,
    force: bool = False,
) -> Path:
    """Fetch CLDR likelySubtags.json and save it gzipped.

    URL and version are read from config. Used separately when the
    data needs updating.

    Returns the path to the saved file.
    """
    cldr = _get_cldr_config(config)
    local_file = _cldr_local_file()

    if local_file.exists() and not force:
        log.info("CLDR data already exists: %s", local_file)
        return local_file

    log.info(
        "Downloading CLDR %s: %s", cldr["version"], cldr["url"]
    )

    req = urllib.request.Request(
        cldr["url"],
        headers={"User-Agent": cldr["user_agent"]},
    )

    try:
        with safe_urlopen(req, timeout=cldr["timeout"]) as resp:
            data = read_limited_response(resp, MAX_DOWNLOAD_BYTES)
    except SafeHTTPError as exc:
        raise _safe_http_to_operational(exc, source="cldr") from exc

    try:
        local_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = local_file.with_suffix(local_file.suffix + ".tmp")
        with gzip.open(tmp, "wb") as f:
            f.write(data)
            f.flush()
    except OSError as e:
        raise OperationalError(
            f"Could not write {local_file}: {e}",
            source="filesystem",
            kind="transport",
        ) from e
    tmp.replace(local_file)

    log.info(
        "Saved: %s (%.1f kB)",
        local_file, local_file.stat().st_size / 1024,
    )
    return local_file


def load_cldr_likely_subtags(config: dict) -> dict:
    """Read bundled CLDR likelySubtags data.

    Returns a dict of the form: {"fi": "fi-Latn-FI", ...}
    (CLDR 48+ uses hyphens, not underscores.)

    Does NOT hit the network if the file exists. If the file is
    missing, tries to fetch it once (fetch_cldr_likely_subtags).
    """
    local_file = _cldr_local_file()

    if not local_file.exists():
        log.warning(
            "CLDR data missing, trying to fetch: %s", local_file
        )
        fetch_cldr_likely_subtags(config)

    try:
        with gzip.open(local_file, "rt", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise DataError(
            f"Could not read {local_file}: {e}",
            source="cldr",
        ) from e

    subtags = raw.get("supplemental", {}).get("likelySubtags", {})
    if not subtags:
        raise DataError(
            f"CLDR file {local_file} does not contain "
            f"likelySubtags data",
            source="cldr",
        )

    log.info(
        "Loaded %d CLDR likelySubtags rules", len(subtags)
    )
    return subtags


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Fetch CLDR likelySubtags.json gzipped.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force re-download (ignore existing file)",
    )
    args = parser.parse_args()

    try:
        config = load_config()
        path = fetch_cldr_likely_subtags(
            config, force=args.force
        )
    except OperationalError as exc:
        log.error("Source error: %s", exc)
        if exc.retryable:
            log.error("Error is temporary - try again later.")
        return 1
    except DataError as exc:
        log.error("Data error: %s", exc)
        return 1

    print(f"Done: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
