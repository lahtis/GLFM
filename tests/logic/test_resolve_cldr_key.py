# tests/logic/test_resolve_cldr_key.py
"""Tests for resolve_cldr_key."""

from glfm.logic.resolve_cldr_key import resolve_cldr_key


class TestResolveCldrKey:
    def test_uses_iso639_1(self) -> None:
        assert (
            resolve_cldr_key("fin", {"iso639_1": "fi"}) == "fi"
        )

    def test_iso639_1_is_lowercased(self) -> None:
        assert (
            resolve_cldr_key("fin", {"iso639_1": "FI"}) == "fi"
        )

    def test_iso639_1_is_stripped(self) -> None:
        assert (
            resolve_cldr_key("fin", {"iso639_1": " fi "}) == "fi"
        )

    def test_falls_back_to_lang_id(self) -> None:
        assert resolve_cldr_key("yok", {}) == "yok"

    def test_none_iso_info(self) -> None:
        assert resolve_cldr_key("fin", None) == "fin"

    def test_empty_iso639_1(self) -> None:
        assert (
            resolve_cldr_key("fin", {"iso639_1": ""}) == "fin"
        )

    def test_unknown_iso639_1(self) -> None:
        assert (
            resolve_cldr_key("fin", {"iso639_1": "UNKNOWN"}) == "fin"
        )

    def test_non_string_iso639_1(self) -> None:
        assert resolve_cldr_key("fin", {"iso639_1": 123}) == "fin"
