# src/glfm/errors.py
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.1.0
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
# GLFM error hierarchy.
#
# All user-facing errors inherit from GlfmError.
# Everything else (Exception) is a bug and should be handled with
# log.exception().
#
# OperationalError carries a `source` field (which source failed),
# a `kind` field (SafeHTTPError.kind), `temporary` and `retryable`
# (whether the error can be retried).
#
# Relationship to SafeHTTPError:
#   - SafeHTTPError is an internal class in
#     glfm.utils.safe_http_common.
#   - It does NOT inherit from GlfmError — it is vendored SHL code.
#   - Callers (fetch_from_wikidata, download.py) translate
#     SafeHTTPError -> OperationalError and forward kind.
#

from __future__ import annotations


class GlfmError(Exception):
    """Base for all user-facing errors.

    Subclasses indicate the cause of the error, and main() can handle
    them differently (e.g. ConfigError -> advise the user,
    OperationalError -> tell whether the error is temporary).
    """


class ConfigError(GlfmError):
    """Config is missing or invalid.

    E.g. config.toml is missing, TOML is broken, or a required key
    (e.g. sources.wikidata.endpoint) is missing.
    """


class OperationalError(GlfmError):
    """Network, HTTP, rate limit, source not responding.

    `source` indicates which source failed (e.g. "iso_639_3",
    "wikidata", "download.consumer").

    `kind` indicates the specific cause (same value as
    SafeHTTPError.kind): "timeout", "transport", "security",
    "http_status", "invalid_response", "invalid_content_type",
    "response_too_large".

    `status_code` is the HTTP status, if known (e.g. 429, 500).

    `temporary` and `retryable` indicate whether the error can be
    retried:
        - timeout:           temporary=True,  retryable=True
        - transport:         temporary=True,  retryable=True
        - http_status 429:   temporary=True,  retryable=True
        - http_status 503:   temporary=True,  retryable=True
        - http_status 404:   temporary=False, retryable=False
        - security:          temporary=False, retryable=False
        - invalid_response:  temporary=False, retryable=False
    """

    def __init__(
        self,
        message: str,
        *,
        source: str = "",
        kind: str = "transport",
        status_code: int | None = None,
        temporary: bool = False,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.source = source
        self.kind = kind
        self.status_code = status_code
        self.temporary = temporary
        self.retryable = retryable

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.source:
            parts.append(f"source={self.source}")
        if self.kind:
            parts.append(f"kind={self.kind}")
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        return " ".join(parts)


class DataError(GlfmError):
    """Data (local or remote) does not match the expected schema.

    `source` indicates which source produced the invalid data
    (e.g. "iso_639_3", "wikidata", "languoids.json").

    E.g. JSON did not parse, a required field is missing, or a value
    has the wrong type.
    """

    def __init__(self, message: str, *, source: str = "") -> None:
        super().__init__(message)
        self.source = source

    def __str__(self) -> str:
        if self.source:
            return f"{super().__str__()} (source={self.source})"
        return super().__str__()
