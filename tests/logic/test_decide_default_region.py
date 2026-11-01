# tests/logic/test_decide_default_region.py
"""Tests for decide_default_region."""

from glfm.logic.decide_default_region import decide_default_region


class TestDecideDefaultRegion:
    def test_cldr_region(self) -> None:
        cldr = {"fi": "fi-Latn-FI"}
        assert (
            decide_default_region("fin", None, cldr, {"iso639_1": "fi"})
            == "FI"
        )

    def test_cldr_region_is_uppercased(self) -> None:
        cldr = {"fi": "fi-Latn-fi"}
        assert (
            decide_default_region("fin", None, cldr, {"iso639_1": "fi"})
            == "FI"
        )

    def test_wiktionary_region_fallback(self) -> None:
        wikt = {"region": "US"}
        assert decide_default_region("yok", wikt, {}, {}) == "US"

    def test_wiktionary_unknown_region_skipped(self) -> None:
        wikt = {"region": "UNKNOWN"}
        assert decide_default_region("yok", wikt, {}, {}) == "001"

    def test_fallback_to_001(self) -> None:
        assert decide_default_region("xxx", None, {}, {}) == "001"

    def test_cldr_takes_precedence_over_wiktionary(self) -> None:
        cldr = {"fi": "fi-Latn-FI"}
        wikt = {"region": "US"}
        assert (
            decide_default_region("fin", wikt, cldr, {"iso639_1": "fi"})
            == "FI"
        )
