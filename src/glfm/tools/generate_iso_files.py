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
# Download ISO 639 sources and generate Python modules into data/.
# Produces: iso_639_1.py, iso_639_2.py, iso_639_3.py,
#           iso_639_3_names.py, iso_639_3_macrolanguages.py,
#           iso_639_5.py
#
# URLs and settings are read from config (glfm.config / config.toml /
# environment variables). No hardcoded URLs.
#
# All outbound HTTP goes through glfm.utils.safe_http (vendored from SHL).
#

import logging
import os
import urllib.request
from pathlib import Path

from glfm.config import load_config
from glfm.errors import OperationalError
from glfm.paths import get_data_dir
from glfm.utils.safe_http import safe_urlopen
from glfm.utils.safe_http_common import (
    SafeHTTPError,
    read_limited_response,
)

log = logging.getLogger(__name__)

# Upper bound per ISO source (these are small files, <1 MB).
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# Minimum plausible size for an ISO source file.
MIN_DOWNLOAD_BYTES = 500


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


def _get_source_config(config: dict, key: str) -> dict:
    """Return config['sources'][key] or raise OperationalError."""
    sources = config.get("sources", {})
    if key not in sources:
        raise OperationalError(
            f"Config: sources.{key} is missing",
            source=key,
            kind="invalid_response",
        )
    return sources[key]


def safe_download(
    url_key: str,
    config: dict,
    timeout: int | None = None,
) -> Path:
    """Download one source from config and save it to data/.

    Args:
        url_key: config['sources'][key] — e.g. "iso_639_3"
        config: load_config() result
        timeout: overrides config['http']['timeout']
    """
    source = _get_source_config(config, url_key)
    url = source.get("url")
    if not url:
        raise OperationalError(
            f"Config: sources.{url_key}.url is missing",
            source=url_key,
            kind="invalid_response",
        )

    http = config.get("http", {})
    user_agent = http["user_agent"]
    timeout = timeout or http.get("timeout", 60)

    data_dir = get_data_dir()
    suffix = ".rdf" if url_key == "iso_639_5" else ".tab"
    out = data_dir / f"{url_key}{suffix}"

    log.info("Downloading %s: %s", url_key, url)

    req = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent},
    )

    try:
        with safe_urlopen(req, timeout=timeout) as resp:
            content = read_limited_response(resp, MAX_DOWNLOAD_BYTES)
    except SafeHTTPError as exc:
        raise _safe_http_to_operational(exc, source=url_key) from exc

    if len(content) < MIN_DOWNLOAD_BYTES:
        raise OperationalError(
            f"Downloaded file too small ({len(content)} bytes): {url_key}",
            source=url_key,
            kind="invalid_response",
        )

    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        with open(out, "wb") as f:
            f.write(content)
    except OSError as e:
        raise OperationalError(
            f"Could not write {out}: {e}",
            source="filesystem",
            kind="transport",
        ) from e

    log.info("Saved: %s (%.1f kB)", out, len(content) / 1024)
    return out


def generate_iso_modules() -> None:
    config = load_config()
    data_dir = get_data_dir()

    log.info("=== Downloading ISO sources ===")
    log.info("Data directory: %s", data_dir)

    tab3 = safe_download("iso_639_3", config)
    tab_names = safe_download("iso_639_3_names", config)
    tab_macro = safe_download("iso_639_3_macrolanguages", config)
    rdf5 = safe_download("iso_639_5", config)

    log.info("=== Parsing ISO files ===")

    from glfm.tools.parse_iso_files import parse_all_iso_files

    data = parse_all_iso_files(tab3, tab_names, tab_macro, rdf5)

    log.info("=== Writing Python modules to data/ ===")

    modules = {
        "iso_639_1.py": f"iso_639_1 = {data['iso639_1']}\n",
        "iso_639_2.py": f"iso_639_2 = {data['iso639_2']}\n",
        "iso_639_3.py": f"iso_639_3 = {data['iso639_3']}\n",
        "iso_639_3_names.py": f"iso_639_3_names = {data['iso639_3_names']}\n",
        "iso_639_3_macrolanguages.py": (
            f"iso_639_3_macrolanguages = {data['iso639_3_macrolanguages']}\n"
        ),
        "iso_639_5.py": f"iso_639_5 = {data['iso639_5']}\n",
    }

    for name, content in modules.items():
        _atomic_write_text(data_dir / name, content)
        log.info("Written: %s", name)

    log.info("All ISO modules generated successfully.")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        generate_iso_modules()
    except OperationalError as exc:
        log.error("Source error: %s", exc)
        if exc.retryable:
            log.error("Error is temporary — try again later.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
