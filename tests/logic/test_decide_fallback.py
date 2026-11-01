# tests/logic/test_decide_fallback.py
"""Tests for decide_fallback."""

from glfm.logic.decide_fallback import decide_fallback


class TestDecideFallback:
    def test_no_wiktionary_returns_lang_id(self) -> None:
        assert decide_fallback("fin", None) == "fin"

    def test_empty_wiktionary_returns_lang_id(self) -> None:
        assert decide_fallback("fin", {}) == "fin"

    def test_wiktionary_without_parent(self) -> None:
        assert decide_fallback("fin", {"name": "Finnish"}) == "fin"

    def test_wiktionary_with_parent(self) -> None:
        assert decide_fallback("fin", {"parent": "urj"}) == "urj"

    def test_parent_is_lowercased(self) -> None:
        assert decide_fallback("fin", {"parent": "URJ"}) == "urj"

    def test_parent_is_stripped(self) -> None:
        assert decide_fallback("fin", {"parent": " urj "}) == "urj"

    def test_unknown_parent_returns_lang_id(self) -> None:
        assert decide_fallback("fin", {"parent": "UNKNOWN"}) == "fin"

    def test_empty_parent_returns_lang_id(self) -> None:
        assert decide_fallback("fin", {"parent": ""}) == "fin"

    def test_non_string_parent_returns_lang_id(self) -> None:
        assert decide_fallback("fin", {"parent": 123}) == "fin"
