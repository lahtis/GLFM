"""Integration coverage for ISO 639-5 assignment in unified records."""

import glfm.build_unified as builder


def test_build_unified_assigns_iso639_5_code(monkeypatch) -> None:
    monkeypatch.setattr(
        builder,
        "load_iso_639",
        lambda: {
            "fin": {
                "name": "Finnish",
                "iso639_1": "fi",
                "iso639_2B": "fin",
                "iso639_2T": "fin",
                "iso639_3": "fin",
                "language_type": "L",
            }
        },
    )
    monkeypatch.setattr(
        builder,
        "load_iso_639_5",
        lambda: {"urj": {"name": "Uralic languages"}},
    )
    monkeypatch.setattr(builder, "load_cldr_likely_subtags", lambda _config: {})
    monkeypatch.setattr(builder, "load_wiktionary_languages", lambda: {})
    monkeypatch.setattr(builder, "load_written_languages", lambda: {})
    monkeypatch.setattr(
        builder,
        "load_glottolog",
        lambda: {"fin": {"glottocode": "finn1318", "family": "Finnic"}},
    )
    monkeypatch.setattr(builder, "load_pos_stats", lambda: {})
    monkeypatch.setattr(builder, "load_uralic_languages", lambda: set())
    monkeypatch.setattr(builder, "load_override_scripts", lambda: {})

    result = builder.build_unified({})

    assert result["fin"]["iso639_3"] == "fin"
    assert result["fin"]["iso639_5"] == "urj"
