# tests/loaders/test_load_languoids.py
"""Tests for load_from_languoids_json."""

import json
from pathlib import Path

import pytest

from glfm.loaders.load_glottolog import load_from_languoids_json


class TestLoadFromLanguoidsJson:
    """Test load_from_languoids_json behavior."""

    def test_returns_dict_keyed_by_iso3(self, mini_languoids: Path) -> None:
        result = load_from_languoids_json(mini_languoids)
        assert isinstance(result, dict)
        # Validit kielet ovat mukana
        assert "fin" in result
        assert "est" in result

    def test_skips_entries_without_iso639_3(self, mini_languoids: Path) -> None:
        result = load_from_languoids_json(mini_languoids)
        # xxxx1234:lla ei ole iso639_3:a
        # Sitä ei voi tunnistaa avaimen perusteella, mutta
        # varmistetaan ettei se ole päätynyt mihinkään
        glottocodes = {v["glottocode"] for v in result.values()}
        assert "xxxx1234" not in glottocodes

    def test_skips_wrong_length_iso3(self, mini_languoids: Path) -> None:
        result = load_from_languoids_json(mini_languoids)
        # "finnish" (7) ja "fi" (2) hylätään
        assert "finnish" not in result
        assert "fi" not in result

    def test_skips_none_iso3(self, mini_languoids: Path) -> None:
        result = load_from_languoids_json(mini_languoids)
        assert None not in result

    def test_preserves_unicode(self, mini_languoids: Path) -> None:
        result = load_from_languoids_json(mini_languoids)
        # "sme" on validi, family "Sámi" säilyy UTF-8:na
        assert "sme" in result
        assert result["sme"]["family"] == "Sámi"

    def test_latitude_string_is_copied_as_is(self, mini_languoids: Path) -> None:
        """Dokumentoi nykyinen käyttäytyminen: latitude kopioidaan sellaisenaan."""
        result = load_from_languoids_json(mini_languoids)
        # "edge1234" -> "xxx" on validi ISO, latitude on merkkijono
        assert "xxx" in result
        # Tämä on NYKYINEN käyttäytyminen: ei konversiota
        # Jos haluat konversion, muuta koodia ja tätä testiä
        assert result["xxx"]["latitude"] == "not-a-number"

    def test_empty_file(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.json"
        path.write_text("[]", encoding="utf-8")
        assert load_from_languoids_json(path) == {}

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            load_from_languoids_json(path)

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("not json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_from_languoids_json(path)

    def test_result_structure(self, mini_languoids: Path) -> None:
        result = load_from_languoids_json(mini_languoids)
        fin = result["fin"]
        # Kentät, jotka pitäisi olla
        assert fin["iso639_3"] == "fin"
        assert fin["glottocode"] == "finn1318"
        assert fin["family"] == "Finnic"
        assert fin["latitude"] == 62.0
        assert fin["longitude"] == 25.0
        assert fin["lineage"] == []
        assert fin["macroarea"] is None  # puuttuu datasta
        assert fin["status"] == ""  # oletus
