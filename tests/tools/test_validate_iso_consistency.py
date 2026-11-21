"""Tests for ISO code validation in the unified language database."""

from glfm.tools.validate_iso_consistency import validate_iso


def test_iso639_3_language_may_also_have_iso639_5_group_code() -> None:
    data = {
        "fin": {
            "iso639_3": "fin",
            "iso639_5": "urj",
        }
    }

    assert validate_iso(data) == []


def test_invalid_iso639_5_code_is_reported() -> None:
    data = {"fin": {"iso639_3": "fin", "iso639_5": "ural"}}

    assert validate_iso(data) == ["fin: invalid iso639_5 'ural'"]


def test_iso639_5_code_must_exist_in_official_registry() -> None:
    data = {"fin": {"iso639_3": "fin", "iso639_5": "abc"}}

    assert validate_iso(data, {"urj", "ine"}) == [
        "fin: iso639_5 'abc' is not in the ISO 639-5 registry"
    ]


def test_iso639_5_registry_member_passes() -> None:
    data = {"fin": {"iso639_3": "fin", "iso639_5": "urj"}}

    assert validate_iso(data, {"urj", "ine"}) == []
