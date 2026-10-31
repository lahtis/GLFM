# tests/utils/test_safe_http_glfm.py
"""GLFM-specific smoke tests for vendored safe_http."""

import pytest

from glfm.utils.safe_http import safe_urlopen
from glfm.utils.safe_http_common import SafeHTTPError


class TestSafeHttpGlfm:
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
        with pytest.raises(SafeHTTPError):
            safe_urlopen("https://query.wikidata.org/sparql")
        assert captured["ua"].startswith("glfm/")
