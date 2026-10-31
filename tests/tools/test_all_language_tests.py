# tests/tools/test_all_language_tests.py
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.1.0
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
# Tests for validate() in glfm.tools.all_language_tests.
# Pure function: no file writes, no network. Fast.
#

import pytest

from glfm.tools.all_language_tests import validate


# --- Helpers --------------------------------------------------------------

def _lang(
    *,
    bcp47: str = "fi-Latn-FI",
    script: str = "Latn",
    region: str = "FI",
    written: bool = True,
    scripts: list[str] | None = None,
    uralic: bool = False,
) -> dict:
    """Build a language entry for tests."""
    return {
        "bcp47": bcp47,
        "default_script": script,
        "default_region": region,
        "written": written,
        "written_scripts": (
            ["Latn"] if scripts is None else scripts
        ),
        "uralicNLP": uralic,
    }


# --- Happy path -----------------------------------------------------------

class TestValidLanguages:
    def test_valid_language_no_errors(self):
        unified = {"fin": _lang()}
        all_langs, errors = validate(unified)
        assert len(all_langs) == 1
        assert all_langs[0]["id"] == "fin"
        assert all_langs[0]["bcp47"] == "fi-Latn-FI"
        assert errors == []

    def test_multiple_valid_languages(self):
        unified = {
            "fin": _lang(bcp47="fi-Latn-FI", region="FI"),
            "est": _lang(bcp47="et-Latn-EE", region="EE"),
            "eng": _lang(bcp47="en-Latn-US", region="US"),
        }
        all_langs, errors = validate(unified)
        assert len(all_langs) == 3
        assert errors == []

    def test_non_written_language_ok(self):
        """Non-written languages may have empty script."""
        unified = {"xxx": _lang(
            bcp47="xx", script="", region="",
            written=False, scripts=[],
        )}
        _, errors = validate(unified)
        assert errors == []

    def test_uralic_flag_preserved(self):
        unified = {"fin": _lang(uralic=True)}
        all_langs, _ = validate(unified)
        assert all_langs[0]["uralicNLP"] is True


# --- Test 1: written=True requires a script ------------------------------

class TestWrittenButNoScript:
    def test_written_without_script(self):
        unified = {"xxx": _lang(
            bcp47="xx", script="", written=True, scripts=[],
        )}
        _, errors = validate(unified)
        types = {e["type"] for e in errors}
        assert "written_but_no_script" in types

    def test_written_with_script_ok(self):
        unified = {"fin": _lang(script="Latn", written=True)}
        _, errors = validate(unified)
        assert "written_but_no_script" not in {
            e["type"] for e in errors
        }


# --- Test 1b: UNKNOWN sentinel -------------------------------------------

class TestUnknownSentinel:
    def test_script_is_unknown_sentinel(self):
        unified = {"xxx": _lang(
            bcp47="xx", script="UNKNOWN",
            written=True, scripts=["UNKNOWN"],
        )}
        _, errors = validate(unified)
        types = {e["type"] for e in errors}
        assert "script_is_unknown_sentinel" in types

    def test_unknown_case_insensitive(self):
        unified = {"xxx": _lang(
            bcp47="xx", script="unknown",
            written=True, scripts=["unknown"],
        )}
        _, errors = validate(unified)
        types = {e["type"] for e in errors}
        assert "script_is_unknown_sentinel" in types
        assert "written_scripts_contains_unknown" in types

    def test_normal_script_not_flagged(self):
        unified = {"fin": _lang(script="Latn")}
        _, errors = validate(unified)
        assert "script_is_unknown_sentinel" not in {
            e["type"] for e in errors
        }


# --- Test 2: written flag vs. script list --------------------------------

class TestWrittenFlagConsistency:
    def test_written_but_empty_scripts(self):
        unified = {"xxx": _lang(
            bcp47="xx-Latn", script="Latn",
            written=True, scripts=[],
        )}
        _, errors = validate(unified)
        types = {e["type"] for e in errors}
        assert "written_but_empty_scripts" in types

    def test_not_written_but_has_scripts(self):
        unified = {"xxx": _lang(
            bcp47="xx", script="", region="",
            written=False, scripts=["Latn"],
        )}
        _, errors = validate(unified)
        types = {e["type"] for e in errors}
        assert "not_written_but_has_scripts" in types

    def test_consistent_flags_ok(self):
        unified = {"fin": _lang(written=True, scripts=["Latn"])}
        _, errors = validate(unified)
        assert "written_but_empty_scripts" not in {
            e["type"] for e in errors
        }
        assert "not_written_but_has_scripts" not in {
            e["type"] for e in errors
        }


# --- Test 3: written_scripts contains UNKNOWN ----------------------------

class TestWrittenScriptsUnknown:
    def test_script_list_contains_unknown(self):
        unified = {"xxx": _lang(
            bcp47="xx-Latn", script="Latn",
            written=True, scripts=["Latn", "UNKNOWN"],
        )}
        _, errors = validate(unified)
        types = {e["type"] for e in errors}
        assert "written_scripts_contains_unknown" in types

    def test_break_after_first_unknown(self):
        """Only one error per language, even with multiple UNKNOWNs."""
        unified = {"xxx": _lang(
            bcp47="xx-Latn", script="Latn",
            written=True, scripts=["UNKNOWN", "UNKNOWN"],
        )}
        _, errors = validate(unified)
        count = sum(
            1 for e in errors
            if e["type"] == "written_scripts_contains_unknown"
        )
        assert count == 1


# --- Test 4: BCP47 invalid values ----------------------------------------

class TestBcp47Invalid:
    def test_bcp47_contains_unknown(self):
        unified = {"xxx": _lang(
            bcp47="xx-Latn-UNKNOWN", script="Latn",
        )}
        _, errors = validate(unified)
        types = {e["type"] for e in errors}
        assert "bcp47_invalid_value" in types

    def test_bcp47_contains_001(self):
        unified = {"xxx": _lang(
            bcp47="xx-Latn-001", script="Latn",
            region="001",
        )}
        _, errors = validate(unified)
        types = {e["type"] for e in errors}
        assert "bcp47_invalid_value" in types

    def test_bcp47_clean_ok(self):
        unified = {"fin": _lang(bcp47="fi-Latn-FI")}
        _, errors = validate(unified)
        assert "bcp47_invalid_value" not in {
            e["type"] for e in errors
        }


# --- Test 5: region 001 in BCP47 -----------------------------------------

class TestRegion001InBcp47:
    def test_region_001_with_bcp47_001(self):
        unified = {"xxx": _lang(
            bcp47="xx-Latn-001", script="Latn", region="001",
        )}
        _, errors = validate(unified)
        types = {e["type"] for e in errors}
        # Both test 4 and test 5 should fire
        assert "bcp47_invalid_value" in types
        assert "region_001_in_bcp47" in types

    def test_region_001_without_bcp47_001_ok(self):
        """Region 001 but BCP47 doesn't contain -001: no error."""
        unified = {"xxx": _lang(
            bcp47="xx", script="Latn", region="001",
        )}
        _, errors = validate(unified)
        assert "region_001_in_bcp47" not in {
            e["type"] for e in errors
        }


# --- Structural / output shape -------------------------------------------

class TestOutputShape:
    def test_all_langs_list_has_expected_fields(self):
        unified = {"fin": _lang(uralic=True)}
        all_langs, _ = validate(unified)
        entry = all_langs[0]
        assert set(entry.keys()) == {
            "id", "bcp47", "default_script", "default_region",
            "written", "written_scripts", "uralicNLP",
        }

    def test_errors_have_id_type_value(self):
        unified = {"xxx": _lang(
            bcp47="xx", script="", written=True, scripts=[],
        )}
        _, errors = validate(unified)
        assert errors
        for e in errors:
            assert "id" in e
            assert "type" in e
            assert "value" in e

    def test_empty_input(self):
        all_langs, errors = validate({})
        assert all_langs == []
        assert errors == []

    def test_booleans_coerced(self):
        """written and uralicNLP are bool() coerced."""
        unified = {"xxx": {
            "bcp47": "xx",
            "default_script": "Latn",
            "default_region": "",
            "written": 1,        # truthy int
            "written_scripts": ["Latn"],
            "uralicNLP": None,   # falsy None
        }}
        all_langs, _ = validate(unified)
        assert all_langs[0]["written"] is True
        assert all_langs[0]["uralicNLP"] is False


# --- Multiple errors for the same language -------------------------------

class TestMultipleErrors:
    def test_language_can_have_multiple_errors(self):
        unified = {"xxx": _lang(
            bcp47="xx-UNKNOWN-001",
            script="UNKNOWN",
            region="001",
            written=True,
            scripts=["UNKNOWN"],
        )}
        _, errors = validate(unified)
        types = {e["type"] for e in errors}
        # Several checks should fire
        assert "script_is_unknown_sentinel" in types
        assert "written_scripts_contains_unknown" in types
        assert "bcp47_invalid_value" in types
        assert "region_001_in_bcp47" in types

    def test_multiple_languages_isolated(self):
        """Errors for one language don't affect another."""
        unified = {
            "fin": _lang(),  # valid
            "xxx": _lang(
                bcp47="xx", script="", written=True, scripts=[],
            ),
        }
        _, errors = validate(unified)
        # Only xxx has errors
        ids = {e["id"] for e in errors}
        assert ids == {"xxx"}
