# tests/logic/test_decide_default_script.py
"""Tests for decide_default_script."""

from glfm.logic.decide_default_script import decide_default_script


class TestDecideDefaultScript:
    def test_override_takes_precedence(self) -> None:
        overrides = {"grc": ["Grek", "Linb"]}
        assert (
            decide_default_script(
                "grc", None, {}, None, {}, overrides
            )
            == "Grek"
        )

    def test_written_scripts(self) -> None:
        written = {"scripts": ["Latn"]}
        assert (
            decide_default_script(
                "fin", None, {}, written, {}
            )
            == "Latn"
        )

    def test_cldr_script(self) -> None:
        cldr = {"fi": "fi-Latn-FI"}
        assert (
            decide_default_script(
                "fin", None, cldr, None, {"iso639_1": "fi"}
            )
            == "Latn"
        )

    def test_wiktionary_script(self) -> None:
        wikt = {"scripts": ["Latn"]}
        assert (
            decide_default_script("yok", wikt, {}, None, {})
            == "Latn"
        )

    def test_no_script_returns_empty(self) -> None:
        assert decide_default_script("xxx", None, {}, None, {}) == ""

    def test_unknown_script_skipped(self) -> None:
        written = {"scripts": ["UNKNOWN"]}
        assert (
            decide_default_script("fin", None, {}, written, {})
            == ""
        )

    def test_invalid_script_skipped(self) -> None:
        written = {"scripts": ["latn"]}  # lowercase is invalid
        assert (
            decide_default_script("fin", None, {}, written, {})
            == ""
        )

    def test_override_accepts_string(self) -> None:
        overrides = {"grc": "Grek"}
        assert (
            decide_default_script(
                "grc", None, {}, None, {}, overrides
            )
            == "Grek"
        )
