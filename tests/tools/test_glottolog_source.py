"""Tests for Glottolog source provenance and Wikidata fallback tracking."""

from glfm.errors import OperationalError
from glfm.tools import build_glottolog_json as builder


def test_records_official_glottolog_as_source(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(builder, "get_data_dir", lambda: tmp_path)
    monkeypatch.setattr(
        builder,
        "fetch_from_glottolog",
        lambda _config: {
            "fin": {"glottocode": "finn1318", "lineage": ["ural1272"]}
        },
    )

    data, provenance = builder.build_glottolog({}, with_source=True)

    assert "fin" in data
    assert provenance["source"] == "glottolog_official"
    assert provenance["record_count"] == 1
    assert provenance["lineage_count"] == 1


def test_records_wikidata_when_official_source_fails(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(builder, "get_data_dir", lambda: tmp_path)

    def fail_glottolog(_config):
        raise OperationalError("unavailable", source="glottolog")

    monkeypatch.setattr(builder, "fetch_from_glottolog", fail_glottolog)
    monkeypatch.setattr(
        builder,
        "fetch_from_wikidata",
        lambda _config: {"fin": {"glottocode": "finn1318", "lineage": []}},
    )

    data, provenance = builder.build_glottolog({}, with_source=True)

    assert "fin" in data
    assert provenance["source"] == "wikidata_fallback"
    assert provenance["record_count"] == 1
    assert provenance["lineage_count"] == 0


def test_force_wikidata_bypasses_official_source(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(builder, "get_data_dir", lambda: tmp_path)
    monkeypatch.setattr(
        builder,
        "fetch_from_wikidata",
        lambda _config: {"fin": {"glottocode": "finn1318", "lineage": []}},
    )
    monkeypatch.setattr(
        builder,
        "fetch_from_glottolog",
        lambda _config: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    _data, provenance = builder.build_glottolog(
        {}, force_wikidata=True, with_source=True
    )

    assert provenance["source"] == "wikidata_forced"
