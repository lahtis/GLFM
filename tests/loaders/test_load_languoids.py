# tests/loaders/test_load_languoids.py
"""Tests for load_from_languoids_json."""

from pathlib import Path

import pytest

from glfm.errors import DataError, OperationalError
from glfm.tools.build_glottolog_json import load_from_languoids_json
from glfm.tools.build_glottolog_json import load_from_tree
from glfm.tools.build_glottolog_json import load_from_newick


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


def test_newick_builds_nearest_first_lineage() -> None:
    tree = (
        "(('Finnish [finn1234][fin]-l-':1)"
        "'Finnic [finn1318]':1,'Hungarian [hung1287][hun]-l-':1)"
        "'Uralic [ural1272]':1;\n"
    )
    result = load_from_newick(
        tree,
        {
            "finn1234": {
                "macroarea": "Eurasia",
                "latitude": "62.0",
                "longitude": "25.0",
            }
        },
    )
    assert result["fin"]["glottocode"] == "finn1234"
    assert result["fin"]["macroarea"] == "Eurasia"
    assert result["fin"]["lineage"] == ["finn1318", "ural1272"]
    assert result["fin"]["lineage_names"] == ["Finnic", "Uralic"]
    assert result["hun"]["lineage"] == ["ural1272"]


def test_tree_directory_builds_lineage_names(tmp_path: Path) -> None:
    tree = tmp_path / "tree"
    parent = tree / "uralic" / "finnic"
    parent.mkdir(parents=True)
    (tree / "uralic" / "md.ini").write_text(
        "id = ural1272\nname = Uralic\n", encoding="utf-8"
    )
    (parent / "md.ini").write_text(
        "id = finn1318\nname = Finnic\nlineage = ural1272\n",
        encoding="utf-8",
    )
    (parent / "finnish").mkdir()
    (parent / "finnish" / "md.ini").write_text(
        "id = finn1234\nname = Finnish\niso639-3 = fin\n"
        "lineage = ural1272, finn1318\n",
        encoding="utf-8",
    )

    result = load_from_tree(tree)
    assert result["fin"]["lineage"] == ["finn1318", "ural1272"]
    assert result["fin"]["lineage_names"] == ["Finnic", "Uralic"]
