# tests/models/test_language.py
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.1.0
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
# Tests for the Language dataclass.
#

from glfm.models.language import Language


class TestLanguageDefaults:
    """Test default values for the Language dataclass."""

    def test_minimal_construction(self) -> None:
        lang = Language(
            id="fin",
            name="Finnish",
            official_name="Finnish",
        )
        assert lang.id == "fin"
        assert lang.name == "Finnish"
        assert lang.official_name == "Finnish"

    def test_iso_codes_default_to_empty(self) -> None:
        lang = Language(
            id="fin", name="Finnish", official_name="Finnish"
        )
        assert lang.iso639_1 == ""
        assert lang.iso639_2B == ""
        assert lang.iso639_2T == ""
        assert lang.iso639_3 == ""
        assert lang.iso639_5 == ""

    def test_language_type_defaults_to_empty(self) -> None:
        lang = Language(
            id="fin", name="Finnish", official_name="Finnish"
        )
        assert lang.language_type == ""

    def test_script_and_region_default_to_empty(self) -> None:
        lang = Language(
            id="fin", name="Finnish", official_name="Finnish"
        )
        assert lang.default_script == ""
        assert lang.default_region == ""

    def test_bcp47_defaults_to_empty(self) -> None:
        lang = Language(
            id="fin", name="Finnish", official_name="Finnish"
        )
        assert lang.bcp47 == ""

    def test_fallback_defaults_to_empty(self) -> None:
        lang = Language(
            id="fin", name="Finnish", official_name="Finnish"
        )
        assert lang.fallback == ""

    def test_uralic_defaults_to_false(self) -> None:
        lang = Language(
            id="fin", name="Finnish", official_name="Finnish"
        )
        assert lang.uralicNLP is False

    def test_written_defaults_to_false(self) -> None:
        lang = Language(
            id="fin", name="Finnish", official_name="Finnish"
        )
        assert lang.written is False
        assert lang.written_scripts == []

    def test_glottolog_defaults_to_empty(self) -> None:
        lang = Language(
            id="fin", name="Finnish", official_name="Finnish"
        )
        assert lang.glottocode == ""
        assert lang.family == ""
        assert lang.glottolog == {}

    def test_pos_stats_defaults_to_empty(self) -> None:
        lang = Language(
            id="fin", name="Finnish", official_name="Finnish"
        )
        assert lang.pos_stats == {}


class TestLanguageFields:
    """Test that fields can be set and read back."""

    def test_full_construction(self) -> None:
        lang = Language(
            id="fin",
            name="Finnish",
            official_name="Finnish",
            iso639_1="fi",
            iso639_2B="fin",
            iso639_2T="fin",
            iso639_3="fin",
            iso639_5="",
            language_type="L",
            default_script="Latn",
            default_region="FI",
            bcp47="fi-Latn-FI",
            fallback="fin",
            uralicNLP=True,
            written=True,
            written_scripts=["Latn"],
            glottocode="finn1318",
            family="Finnic",
            glottolog={"glottocode": "finn1318"},
            pos_stats={"noun": 176082, "verb": 42247},
        )
        assert lang.iso639_1 == "fi"
        assert lang.language_type == "L"
        assert lang.default_script == "Latn"
        assert lang.default_region == "FI"
        assert lang.bcp47 == "fi-Latn-FI"
        assert lang.fallback == "fin"
        assert lang.uralicNLP is True
        assert lang.written is True
        assert lang.written_scripts == ["Latn"]
        assert lang.glottocode == "finn1318"
        assert lang.family == "Finnic"
        assert lang.glottolog == {"glottocode": "finn1318"}
        assert lang.pos_stats == {"noun": 176082, "verb": 42247}


class TestToDict:
    """Test the to_dict() method."""

    def test_to_dict_returns_dict(self) -> None:
        lang = Language(
            id="fin", name="Finnish", official_name="Finnish"
        )
        result = lang.to_dict()
        assert isinstance(result, dict)

    def test_to_dict_contains_all_fields(self) -> None:
        lang = Language(
            id="fin", name="Finnish", official_name="Finnish"
        )
        result = lang.to_dict()
        expected_keys = {
            "id",
            "name",
            "official_name",
            "iso639_1",
            "iso639_2B",
            "iso639_2T",
            "iso639_3",
            "iso639_5",
            "language_type",
            "default_script",
            "default_region",
            "bcp47",
            "fallback",
            "uralicNLP",
            "written",
            "written_scripts",
            "glottocode",
            "family",
            "glottolog",
            "pos_stats",
        }
        assert set(result.keys()) == expected_keys

    def test_to_dict_values_match(self) -> None:
        lang = Language(
            id="fin",
            name="Finnish",
            official_name="Finnish",
            iso639_1="fi",
            language_type="L",
            written=True,
            written_scripts=["Latn"],
            pos_stats={"noun": 10},
        )
        result = lang.to_dict()
        assert result["id"] == "fin"
        assert result["iso639_1"] == "fi"
        assert result["language_type"] == "L"
        assert result["written"] is True
        assert result["written_scripts"] == ["Latn"]
        assert result["pos_stats"] == {"noun": 10}

    def test_to_dict_is_a_copy(self) -> None:
        """Mutating the result must not affect the dataclass."""
        lang = Language(
            id="fin", name="Finnish", official_name="Finnish"
        )
        result = lang.to_dict()
        result["id"] = "xxx"
        assert lang.id == "fin"

    def test_to_dict_written_scripts_is_a_copy(self) -> None:
        """Mutating written_scripts in the result must not affect the dataclass."""
        lang = Language(
            id="fin",
            name="Finnish",
            official_name="Finnish",
            written_scripts=["Latn"],
        )
        result = lang.to_dict()
        result["written_scripts"].append("Cyrl")
        assert lang.written_scripts == ["Latn"]

    def test_to_dict_pos_stats_is_a_copy(self) -> None:
        """Mutating pos_stats in the result must not affect the dataclass."""
        lang = Language(
            id="fin",
            name="Finnish",
            official_name="Finnish",
            pos_stats={"noun": 10},
        )
        result = lang.to_dict()
        result["pos_stats"]["noun"] = 999
        assert lang.pos_stats == {"noun": 10}

    def test_to_dict_glottolog_is_a_copy(self) -> None:
        """Mutating glottolog in the result must not affect the dataclass."""
        lang = Language(
            id="fin",
            name="Finnish",
            official_name="Finnish",
            glottolog={"glottocode": "finn1318"},
        )
        result = lang.to_dict()
        result["glottolog"]["glottocode"] = "xxx"
        assert lang.glottolog == {"glottocode": "finn1318"}
