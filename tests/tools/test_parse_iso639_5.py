"""Tests for the Library of Congress ISO 639-5 TSV parser."""

from pathlib import Path

import pytest

from glfm.errors import DataError
from glfm.tools import generate_iso_files
from glfm.tools.parse_iso_files import parse_iso639_5_tsv


def test_parse_iso639_5_tsv_with_labels_and_hierarchy(
    tmp_path: Path,
) -> None:
    source = tmp_path / "iso639-5.tsv"
    source.write_text(
        "URI\tCode\tLabel (English)\tLabel (French)\tHierarchy\n"
        "http://id.loc.gov/vocabulary/iso639-5/urj\turj\t"
        "Uralic languages\tLangues ouraliennes\t"
        "ine (Indo-European languages)\n",
        encoding="utf-8",
    )

    result = parse_iso639_5_tsv(source)

    assert result == {
        "urj": {
            "name": "Uralic languages",
            "hierarchy": "ine (Indo-European languages)",
        }
    }


def test_parse_iso639_5_tsv_extracts_code_from_uri(
    tmp_path: Path,
) -> None:
    source = tmp_path / "iso639-5.tsv"
    source.write_text(
        "URI\tLabel (English)\n"
        "http://id.loc.gov/vocabulary/iso639-5/urj\tUralic languages\n",
        encoding="utf-8",
    )

    assert parse_iso639_5_tsv(source) == {
        "urj": {"name": "Uralic languages"}
    }


def test_parse_iso639_5_tsv_accepts_utf8_bom(tmp_path: Path) -> None:
    source = tmp_path / "iso639-5.tsv"
    source.write_text(
        "\ufeffCode\tLabel (English)\nurj\tUralic languages\n",
        encoding="utf-8",
    )

    assert parse_iso639_5_tsv(source)["urj"]["name"] == "Uralic languages"


def test_parse_iso639_5_tsv_rejects_unrecognized_columns(
    tmp_path: Path,
) -> None:
    source = tmp_path / "iso639-5.tsv"
    source.write_text("Column A\tColumn B\nvalue\tvalue\n", encoding="utf-8")

    with pytest.raises(DataError, match="missing code or English-label"):
        parse_iso639_5_tsv(source)


def test_parse_iso639_5_tsv_rejects_empty_code_list(
    tmp_path: Path,
) -> None:
    source = tmp_path / "iso639-5.tsv"
    source.write_text("Code\tLabel (English)\n", encoding="utf-8")

    with pytest.raises(DataError, match="contained no valid code rows"):
        parse_iso639_5_tsv(source)


def test_download_rewrites_legacy_scheme_url(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, str] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_safe_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = str(timeout)
        return FakeResponse()

    monkeypatch.setattr(generate_iso_files, "get_data_dir", lambda: tmp_path)
    monkeypatch.setattr(generate_iso_files, "safe_urlopen", fake_safe_urlopen)
    monkeypatch.setattr(
        generate_iso_files,
        "read_limited_response",
        lambda _response, _limit: b"x" * 600,
    )
    config = {
        "sources": {
            "iso_639_5": {
                "url": "https://id.loc.gov/vocabulary/iso639-5.skos.rdf"
            }
        },
        "http": {"user_agent": "test-agent", "timeout": 30},
    }

    result = generate_iso_files.safe_download("iso_639_5", config)

    assert captured["url"] == "https://id.loc.gov/vocabulary/iso639-5.tsv"
    assert result.name == "iso_639_5.tsv"
    assert result.read_bytes() == b"x" * 600
