# tests/utils/test_safe_http_glfm.py
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.1.0
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
# GLFM-specific smoke tests for the vendored safe_http layer.
#

import urllib.request

import pytest

from glfm.utils.safe_http import safe_urlopen
from glfm.utils.safe_http_common import SafeHTTPError


class TestSafeHttpGlfm:
    """GLFM-specific smoke tests for safe_http."""

    def test_rejects_http_scheme(self) -> None:
        with pytest.raises(SafeHTTPError) as exc_info:
            safe_urlopen("http://example.com/")
        assert exc_info.value.kind == "security"

    def test_rejects_file_scheme(self) -> None:
        with pytest.raises(SafeHTTPError) as exc_info:
            safe_urlopen("file:///etc/passwd")
        assert exc_info.value.kind == "security"

    def test_rejects_private_ip(self) -> None:
        with pytest.raises(SafeHTTPError) as exc_info:
            safe_urlopen("https://127.0.0.1/")
        assert exc_info.value.kind == "security"

    def test_glfm_user_agent_is_set(self, monkeypatch) -> None:
        captured = {}

        def fake_open(req, timeout):
            captured["ua"] = req.get_header("User-agent")
            raise SafeHTTPError("stop", kind="transport")

        monkeypatch.setattr(
            "glfm.utils.safe_http._opener.open", fake_open
        )

        req = urllib.request.Request(
            "https://query.wikidata.org/sparql",
            headers={"User-Agent": "glfm test"},
        )
        with pytest.raises(SafeHTTPError):
            safe_urlopen(req)

        assert captured["ua"] == "glfm test"
