# tests/errors/test_kind_protocol.py
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.1.0
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
# Guard test: verifies that all OperationalError.kind values are known.
# Same idea as SHL's tests/engine/errors/test_kind_protocol.py, but for
# GLFM's own kind namespace.
#
# If you add a new kind value in the code, add it to KNOWN_KINDS too.
# Otherwise this test will fail — and that is intentional.
#

import re
from pathlib import Path

import pytest

from glfm.errors import DataError, OperationalError


# Known kind namespace. These are the SafeHTTPError.kind values that
# GLFM forwards to OperationalError.
KNOWN_KINDS = {
    # SafeHTTPError.kind (safe_http_common.py)
    "http_error",           # generic HTTP failure
    "transport",            # network/transport failure
    "timeout",              # request timed out
    "security",             # SSRF/scheme/redirect blocked
    "invalid_response",     # JSON decode failed
    "invalid_content_type", # unexpected Content-Type
    "response_too_large",   # response exceeded size limit
    "http_status",          # non-2xx HTTP status (see status_code)
}


def _collect_kinds_from_source() -> set[str]:
    """Find all kind="..." occurrences under src/glfm/."""
    src = Path(__file__).resolve().parent.parent.parent / "src" / "glfm"
    kinds: set[str] = set()
    pattern = re.compile(r'kind\s*=\s*["\']([a-z_]+)["\']')
    for py in src.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            kinds.add(match.group(1))
    return kinds


class TestKindProtocol:
    """Verifies that OperationalError.kind namespace is controlled."""

    def test_known_kinds_are_documented(self) -> None:
        """All kind values in the code are in KNOWN_KINDS."""
        found = _collect_kinds_from_source()
        unknown = found - KNOWN_KINDS
        assert not unknown, (
            f"Unknown kind values in code: {unknown}. "
            f"Add them to KNOWN_KINDS or fix the code."
        )

    def test_known_kinds_are_used(self) -> None:
        """All KNOWN_KINDS values are used somewhere in the code.

        Soft check: if a kind is declared but never used, it may be
        stale. Warning, not error.
        """
        found = _collect_kinds_from_source()
        unused = KNOWN_KINDS - found
        if unused:
            pytest.skip(
                f"KNOWN_KINDS values not used in code: {unused}. "
                f"Consider removing them."
            )


class TestOperationalError:
    """Tests OperationalError fields."""

    def test_default_fields(self) -> None:
        e = OperationalError("test")
        assert e.source == ""
        assert e.kind == "transport"
        assert e.status_code is None
        assert e.temporary is False
        assert e.retryable is False

    def test_full_fields(self) -> None:
        e = OperationalError(
            "test",
            source="wikidata",
            kind="http_status",
            status_code=429,
            temporary=True,
            retryable=True,
        )
        assert e.source == "wikidata"
        assert e.kind == "http_status"
        assert e.status_code == 429
        assert e.temporary is True
        assert e.retryable is True

    def test_str_includes_diagnostics(self) -> None:
        e = OperationalError(
            "timeout",
            source="wikidata",
            kind="timeout",
        )
        s = str(e)
        assert "timeout" in s
        assert "source=wikidata" in s
        assert "kind=timeout" in s


class TestDataError:
    """Tests DataError fields."""

    def test_default_source(self) -> None:
        e = DataError("bad json")
        assert e.source == ""

    def test_source_in_str(self) -> None:
        e = DataError("bad json", source="languoids.json")
        assert "source=languoids.json" in str(e)
