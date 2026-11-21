"""Tests for mapping Glottolog classifications to ISO 639-5 codes."""

from glfm.logic.assign_iso639_5 import assign_iso639_5


ISO639_5_GROUPS = {
    "ine": {"name": "Indo-European languages"},
    "urj": {"name": "Uralic languages"},
}


def test_maps_finnic_family_to_uralic_code() -> None:
    assert assign_iso639_5(
        {"family": "Finnic"}, ISO639_5_GROUPS
    ) == "urj"


def test_maps_glottocode_in_lineage() -> None:
    assert assign_iso639_5(
        {"lineage": ["ural1272", "other9999"]}, ISO639_5_GROUPS
    ) == "urj"


def test_prefers_nearest_mapped_glottolog_ancestor() -> None:
    groups = {
        **ISO639_5_GROUPS,
        "bnt": {"name": "Bantu languages"},
    }
    assert assign_iso639_5(
        {
            "lineage": ["bantu123", "niger123"],
            "lineage_names": ["Bantu", "Niger-Congo"],
        },
        groups,
    ) == "bnt"


def test_maps_glottocode_on_language() -> None:
    assert assign_iso639_5(
        {"glottocode": "finn1318"}, ISO639_5_GROUPS
    ) == "urj"


def test_matches_iso639_5_and_glottolog_family_names() -> None:
    assert assign_iso639_5(
        {"family": "Indo-European"}, ISO639_5_GROUPS
    ) == "ine"


def test_returns_empty_when_no_mapping_exists() -> None:
    assert assign_iso639_5(
        {"family": "Unmapped family"}, ISO639_5_GROUPS
    ) == ""


def test_does_not_return_code_missing_from_downloaded_registry() -> None:
    assert assign_iso639_5(
        {"family": "Finnic"}, {"ine": {"name": "Indo-European languages"}}
    ) == ""
