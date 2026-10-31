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
# Download the Wiktextract dump (~3 GB) to the cache.
# Usage:
#     python3 -m glfm.tools.download_wiktextract
#     python3 -m glfm.tools.download_wiktextract --url <url>
#     python3 -m glfm.tools.download_wiktextract --force
#
# All outbound HTTP goes through glfm.utils.safe_http (vendored from SHL).
# Because the dump is 5-10 GB, this uses chunked streaming (1 MB chunks)
# instead of read_limited_response().
#

import argparse
import hashlib
import logging
import os
import urllib.request
from pathlib import Path

from glfm.errors import OperationalError
from glfm.utils.safe_http import safe_urlopen
from glfm.utils.safe_http_common import SafeHTTPError

log = logging.getLogger(__name__)


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


def _cleanup(path: Path) -> None:
    """Remove a temporary file if it exists."""
    try:
        if path.exists():
            path.unlink()
    except OSError as e:
        log.warning("Could not remove %s: %s", path, e)


def download_wiktextract(
    url: str,
    dest: Path,
    *,
    user_agent: str,
    timeout: int = 3600,
    force: bool = False,
    chunk_size: int = 1024 * 1024,  # 1 MB
) -> Path:
    """Stream-download the Wiktextract dump to `dest`.

    Uses chunked streaming (1 MB) to avoid loading 5-10 GB into memory.
    Shows progress every 100 MB.
    """
    if dest.exists() and not force:
        log.info(
            "Wiktextract dump already exists: %s (%.1f GB)",
            dest, dest.stat().st_size / 1e9,
        )
        return dest

    log.info("Downloading: %s", url)
    log.info("Destination: %s", dest)

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OperationalError(
            f"Could not create directory for {dest}: {e}",
            source="filesystem",
            kind="transport",
        ) from e

    tmp = dest.with_suffix(dest.suffix + ".tmp")
    sha256 = hashlib.sha256()
    downloaded = 0
    last_log = 0

    req = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent},
    )

    try:
        with safe_urlopen(req, timeout=timeout) as resp:
            total_hdr = resp.headers.get("Content-Length")
            total = int(total_hdr) if total_hdr else None

            try:
                with open(tmp, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        sha256.update(chunk)
                        downloaded += len(chunk)

                        if downloaded - last_log >= 100 * 1024 * 1024:
                            if total:
                                pct = downloaded / total * 100
                                log.info(
                                    "  %.1f GB / %.1f GB (%.1f%%)",
                                    downloaded / 1e9,
                                    total / 1e9,
                                    pct,
                                )
                            else:
                                log.info(
                                    "  %.1f GB", downloaded / 1e9
                                )
                            last_log = downloaded

                    f.flush()
                    os.fsync(f.fileno())
            except OSError as e:
                raise OperationalError(
                    f"Could not write {tmp}: {e}",
                    source="filesystem",
                    kind="transport",
                ) from e

        try:
            tmp.replace(dest)
        except OSError as e:
            raise OperationalError(
                f"Could not finalise {dest}: {e}",
                source="filesystem",
                kind="transport",
            ) from e

    except SafeHTTPError as e:
        _cleanup(tmp)
        raise _safe_http_to_operational(e, source="wiktextract") from e
    except OperationalError:
        _cleanup(tmp)
        raise

    log.info("Downloaded: %s (%.1f GB)", dest, downloaded / 1e9)
    log.info("SHA256: %s", sha256.hexdigest())
    return dest


def main() -> int:
    from glfm.config import load_config
    from glfm.paths import get_data_dir

    config = load_config()
    src_cfg = config["sources"].get("wiktextract", {})

    default_url = src_cfg.get("url", "")
    default_filename = src_cfg.get(
        "filename", "raw-wiktextract-data.jsonl.gz"
    )
    default_timeout = src_cfg.get("timeout", 3600)

    # config.py guarantees http.user_agent is present.
    user_agent = config["http"]["user_agent"]

    data_root = get_data_dir()
    default_output = data_root / default_filename

    parser = argparse.ArgumentParser(
        description="Download the Wiktextract dump (~5-10 GB).",
    )
    parser.add_argument(
        "--url", default=default_url,
        help=(
            f"Download URL "
            f"(default: {default_url or 'not configured'})"
        ),
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help=f"Output file (default: {default_output})",
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

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if not args.url:
        log.error(
            "Wiktextract URL missing. Set it in config.toml:\n"
            "  [sources.wiktextract]\n"
            "  url = \"https://...\""
        )
        return 1

    dest = args.output or default_output

    try:
        download_wiktextract(
            args.url, dest,
            user_agent=user_agent,
            timeout=args.timeout,
            force=args.force,
        )
    except OperationalError as exc:
        log.error("Download error: %s", exc)
        if exc.retryable:
            log.error("Error is temporary — try again later.")
        return 1

    print()
    print(f"Wiktextract dump: {dest}")
    print(f"Size: {dest.stat().st_size / 1e9:.1f} GB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
