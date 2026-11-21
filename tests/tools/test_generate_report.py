"""Tests that Markdown and HTML reports include the new audit summary."""

import json

from glfm.tools import generate_report as report


def test_reports_include_iso639_5_and_glottolog_audits(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "unified_languages.json").write_text(
        json.dumps({
            "fin": {
                "iso639_5": "urj",
                "glottocode": "finn1318",
                "glottolog": {"lineage": ["ural1272"]},
            },
            "eng": {
                "iso639_5": "",
                "glottocode": "stan1293",
                "glottolog": {"lineage": []},
            },
        }),
        encoding="utf-8",
    )
    (data_dir / "glottolog_source.json").write_text(
        json.dumps({
            "source": "wikidata_fallback",
            "record_count": 1,
            "lineage_count": 0,
        }),
        encoding="utf-8",
    )
    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()
    (bundled_dir / "uralic_languages.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(report, "get_data_dir", lambda: data_dir)
    monkeypatch.setattr(report, "get_bundled_data_dir", lambda: bundled_dir)
    monkeypatch.setattr(report, "load_iso_639_5", lambda: {"urj": {}})

    def fake_validation(script, timeout=120):
        success = {
            "validate_bcp47.py": "BCP-47 validation OK",
            "validate_fallbacks.py": "All fallback chains are valid.",
            "validate_iso_consistency.py": "All ISO codes are valid.",
            "validate_glottolog.py": "Glottolog validation OK",
        }
        return success[script.name], "", 0

    monkeypatch.setattr(report, "run_validation", fake_validation)
    report.generate_report()

    validation_dir = data_dir / "validation"
    markdown = (validation_dir / "validation_report.md").read_text(encoding="utf-8")
    html = (validation_dir / "validation_report.html").read_text(encoding="utf-8")
    errors = json.loads(
        (validation_dir / "validation_errors.json").read_text(encoding="utf-8")
    )
    assert "ISO 639-5 assignment: **1/2** (50.0%)" in markdown
    assert "ISO 639-5 registry check: OK" in markdown
    assert "Glottolog validation: OK" in markdown
    assert "Glottolog source: **wikidata_fallback**" in markdown
    assert "ISO 639-5 assignment: <strong>1/2</strong> (50.0%)" in html
    assert "ISO 639-5 registry check:" in html
    assert "wikidata_fallback" in html
    assert errors["audit_summary"]["iso639_5_registry_codes"] == 1
    assert errors["audit_summary"]["lineage_records"] == 1
    assert errors["audit_summary"]["glottolog_source"]["source"] == "wikidata_fallback"
