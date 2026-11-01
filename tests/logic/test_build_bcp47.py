# tests/logic/test_build_bcp47.py
"""Tests for build_bcp47."""

from glfm.logic.build_bcp47 import build_bcp47


class TestBuildBcp47:
    def test_language_only(self) -> None:
        assert build_bcp47("fin", "", "", {}) == "fin"

    def test_language_and_script(self) -> None:
        assert build_bcp47("fin", "Latn", "", {}) == "fin-Latn"

    def test_language_and_region(self) -> None:
        assert build_bcp47("fin", "", "FI", {}) == "fin-FI"

    def test_full_tag(self) -> None:
        assert (
            build_bcp47("fin", "Latn", "FI", {"iso639_1": "fi"})
            == "fi-Latn-FI"
        )

    def test_uses_iso639_1_when_available(self) -> None:
        assert (
            build_bcp47("fin", "", "", {"iso639_1": "fi"}) == "fi"
        )

    def test_falls_back_to_lang_id(self) -> None:
        assert build_bcp47("yok", "", "", {}) == "yok"

    def test_skips_unknown_script(self) -> None:
        assert build_bcp47("fin", "UNKNOWN", "", {}) == "fin"

    def test_skips_unknown_region(self) -> None:
        assert build_bcp47("fin", "", "UNKNOWN", {}) == "fin"

    def test_skips_001_region(self) -> None:
        assert build_bcp47("fin", "", "001", {}) == "fin"

    def test_canonical_casing(self) -> None:
        # Script Titlecase, region UPPERCASE
        assert (
            build_bcp47("fin", "latn", "fi", {}) == "fin-Latn-FI"
        )

    def test_strips_whitespace(self) -> None:
        assert (
            build_bcp47("fin", " Latn ", " FI ", {}) == "fin-Latn-FI"
        )
