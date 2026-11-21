"""Tests for structural Glottolog metadata validation."""

from glfm.tools.validate_glottolog import validate_glottolog


def test_valid_glottolog_lineage_passes() -> None:
    assert validate_glottolog({
        "fin": {
            "glottolog": {
                "glottocode": "finn1318",
                "family": "Uralic",
                "lineage": ["finn1317", "ural1272"],
                "lineage_names": ["Finnic", "Uralic"],
                "macroarea": "Eurasia",
                "latitude": 60.0,
                "longitude": 25.0,
            }
        }
    }) == []


def test_invalid_glottocode_and_lineage_are_reported() -> None:
    errors = validate_glottolog({
        "fin": {
            "glottolog": {
                "glottocode": "bad",
                "lineage": ["also-bad"],
                "lineage_names": ["Uralic", "Finnic"],
            }
        }
    })

    assert "fin: invalid Glottocode 'bad'" in errors
    assert "fin: invalid lineage Glottocode 'also-bad'" in errors
    assert "fin: lineage and lineage_names lengths differ" in errors
