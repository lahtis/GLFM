# tests/loaders/test_load_languoids.py
"""Tests for load_from_languoids_json."""

from pathlib import Path

import pytest

from glfm.errors import DataError, OperationalError
from glfm.tools.build_glottolog_json import load_from_languoids_json


class TestLoadFromLanguoidsJson:
    """Test load_from_languoids_json behavior."""

    def test_returns_dict_keyed_by_iso3(self, mini_languoids: Path) -> None:
        result = load_from_languoids_json(mini_languoids)
        assert isinstance(result, dict)
        # Valid languages are included
        assert "fin" in result
        assert "est" in result

    def test_skips_entries_without_iso639_3(self, mini_languoids: Path) -> None:
        result = load_from_languoids_json(mini_languoids)
        # xxxx1234 has no iso639_3; verify it did not end up anywhere
        glottocodes = {v["glottocode"] for v in result.values()}
        assert "xxxx1234" not in glottocodes

    def test_skips_wrong_length_iso3(self, mini_languoids: Path) -> None:
        result = load_from_languoids_json(mini_languoids)
        # "finnish" (7) and "fi" (2) are rejected
        assert "finnish" not in result
        assert "fi" not in result

    def test_skips_none_iso3(self, mini_languoids: Path) -> None:
        result = load_from_languoids_json(mini_languoids)
        assert None not in result

    def test_preserves_unicode(self, mini_languoids: Path) -> None:
        result = load_from_languoids_json(mini_languoids)
        # "sme" is valid; family "Sámi" is preserved as UTF-8
        assert "sme" in result
        assert result["sme"]["family"] == "Sámi"

    def test_latitude_string_is_copied_as_is(self, mini_languoids: Path) -> None:
        """Document current behavior: latitude is copied as-is."""
        result = load_from_languoids_json(mini_languoids)
        # "edge1234" -> "xxx" is a valid ISO code; latitude is a string
        assert "xxx" in result
        # This is CURRENT behavior: no conversion.
        # If you want conversion, change the code and this test.
        assert result["xxx"]["latitude"] == "not-a-number"

    def test_empty_file(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.json"
        path.write_text("[]", encoding="utf-8")
        assert load_from_languoids_json(path) == {}

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.json"
        with pytest.raises(OperationalError):
            load_from_languoids_json(path)

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("not json", encoding="utf-8")
        with pytest.raises(DataError):
            load_from_languoids_json(path)

    def test_result_structure(self, mini_languoids: Path) -> None:
        result = load_from_languoids_json(mini_languoids)
        fin = result["fin"]
        # Fields that should be present
        assert fin["iso639_3"] == "fin"
        assert fin["glottocode"] == "finn1318"
        assert fin["family"] == "Finnic"
        assert fin["latitude"] == 62.0
        assert fin["longitude"] == 25.0
        assert fin["lineage"] == []
        assert fin["macroarea"] is None  # missing from data
        assert fin["status"] == ""  # default
