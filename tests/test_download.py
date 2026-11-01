# tests/test_download.py
"""Tests for glfm.download."""

import pytest

from glfm.utils.safe_http_common import SafeHTTPError
from glfm.errors import OperationalError


def test_download_rejects_unknown_tier():
    from glfm.download import download_data
    with pytest.raises(ValueError):
        download_data(tier="unknown")


def test_download_uses_safe_urlopen(monkeypatch):
    """Verify that safe_urlopen is used (not urllib directly)."""
    called = {}

    def fake_safe_urlopen(url, timeout):
        called["url"] = url
        called["timeout"] = timeout
        raise SafeHTTPError("stop", kind="transport")

    monkeypatch.setattr(
        "glfm.download.safe_urlopen", fake_safe_urlopen
    )
    with pytest.raises(OperationalError):
        from glfm.download import download_data
        download_data(tier="consumer")
    assert "url" in called


def test_download_warns_when_sha256_missing(monkeypatch, caplog):
    """If sha256 is missing, a warning is logged."""
    # ... (existing test)


def test_download_verifies_sha256(monkeypatch):
    """If sha256 is set and wrong, RuntimeError."""
    # ... (existing test)


def test_marker_requires_file(monkeypatch, tmp_path):
    """If marker exists but file is missing, re-download."""
    # ... (existing test)
