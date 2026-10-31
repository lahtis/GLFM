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
# Download a data package to ~/.cache/glfm/data/.
# Usage:
#     python3 -m glfm.download                    # consumer (558 kB)
#     python3 -m glfm.download --tier research    # research (1.4 MB)
#     python3 -m glfm.download --force
#
# All outbound HTTP goes through glfm.utils.safe_http (vendored from SHL).
#

import argparse
import hashlib
import logging
import os
from pathlib import Path

from glfm.errors import OperationalError
from glfm.utils.safe_http import safe_urlopen
from glfm.utils.safe_http_common import (
    SafeHTTPError,
    read_limited_response,
)

log = logging.getLogger(__name__)

TIERS = ("consumer", "research")

# Filename for each tier (saved as-is, .gz)
TIER_FILENAMES = {
    "consumer": "languages_top20.json.gz",
    "research": "unified_languages.json.gz",
}

# Upper bound for a single download (safety net against runaway responses).
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024  # 100 MB


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
    temporary = retryable

    return OperationalError(
        str(exc),
        source=source,
        kind=exc.kind,
        status_code=exc.status_code,
        temporary=temporary,
        retryable=retryable,
    )


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
    filename = TIER_FILENAMES[tier]
    output = cache / filename
    marker = cache / f".downloaded_{tier}"
    source = f"download.{tier}"

    # Check if already downloaded (both marker AND file must exist)
    if (
        cache.exists()
        and marker.exists()
        and output.exists()
        and not force
    ):
        log.info("Data (%s) already exists: %s", tier, output)
        return cache

    # Get tier-specific config
    download_cfg = config["download"].get(tier)
    if not download_cfg:
        raise OperationalError(
            f"Config: download.{tier} is missing. Check config.toml.",
            source=source,
            kind="invalid_response",
        )

    # Try primary URL, then mirrors
    urls = [download_cfg["url"]]
    for _name, url in download_cfg.get("mirrors", {}).items():
        if url != download_cfg["url"]:
            urls.append(url)

    data: bytes | None = None
    last_error: OperationalError | None = None

    for url in urls:
        try:
            log.info("Downloading (%s): %s", tier, url)
            with safe_urlopen(
                url, timeout=download_cfg["timeout"]
            ) as resp:
                data = read_limited_response(resp, MAX_DOWNLOAD_BYTES)
            log.info("Downloaded (%s): %.1f kB", tier, len(data) / 1024)
            break
        except SafeHTTPError as e:
            last_error = _safe_http_to_operational(e, source=source)
            log.warning(
                "Download failed (%s): [%s] %s",
                url, e.kind, e,
            )
            continue
        except OSError as e:
            # safe_urlopen wraps network errors into SafeHTTPError,
            # but catch OSError for disk/permission errors just in case.
            last_error = OperationalError(
                str(e),
                source=source,
                kind="transport",
                temporary=True,
                retryable=True,
            )
            log.warning("Download failed (%s): %s", url, e)
            continue

    if data is None:
        if last_error is not None:
            raise last_error
        raise OperationalError(
            "All downloads failed.",
            source=source,
            kind="transport",
        )

    # Verify hash (skip if not configured — but warn, since this is a
    # security-relevant check).
    expected_sha256 = download_cfg.get("sha256", "")
    if expected_sha256:
        h = hashlib.sha256(data).hexdigest()
        if h != expected_sha256:
            raise OperationalError(
                f"SHA256 mismatch for {tier}: "
                f"got {h}, expected {expected_sha256}",
                source=source,
                kind="invalid_response",
                temporary=False,
                retryable=False,
            )
        log.info("SHA256 verified (%s)", tier)
    else:
        log.warning(
            "No SHA256 configured for %s — download integrity NOT verified. "
            "Set download.%s.sha256 in config.toml for production use.",
            tier, tier,
        )

    # Save as-is (.json.gz) — do NOT extract, do NOT delete cache
    cache.mkdir(parents=True, exist_ok=True)

    tmp = output.with_suffix(output.suffix + ".tmp")
    try:
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(output)
    except OSError as e:
        raise OperationalError(
            f"Could not write {output}: {e}",
            source="filesystem",
            kind="transport",
        ) from e

    # Mark as downloaded
    marker.touch()

    log.info("Done (%s): %s (%.1f kB)", tier, output, len(data) / 1024)
    return cache


def main() -> int:
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
    except OperationalError as exc:
        log.error("Download error: %s", exc)
        if exc.retryable:
            log.error("Error is temporary — try again later.")
        return 1
    except ValueError as exc:
        log.error("Invalid argument: %s", exc)
        return 1

    # Report only the downloaded file's size, not the whole cache.
    filename = TIER_FILENAMES[args.tier]
    output = path / filename
    if output.exists():
        size_kt = output.stat().st_size / 1024
        print()
        print(f"Data ({args.tier}): {output}")
        print(f"Size: {size_kt:.1f} kB")
    else:
        print(f"Data ({args.tier}): {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
