# tests/conftest.py
import json
import pytest
from pathlib import Path


@pytest.fixture
def mini_unified() -> dict:
    """Pieni unified-database testaamiseen."""
    return {
        "fin": {"bcp47": "fi-Latn-FI", "family": "Finnic"},
        "est": {"bcp47": "et-Latn-EE", "family": "Finnic"},
    }


@pytest.fixture
def mini_languoids(tmp_path: Path) -> Path:
    """Monipuolinen languoids.json testaamiseen.

    Sisältää:
    - 2 validia kieltä (fin, est)
    - 1 kielen ilman iso639_3:a (hylätään)
    - 1 kielen väärän pituisella iso639_3:lla (hylätään)
    - 1 kielen None-arvolla (hylätään)
    - 1 kielen, jossa on Unicodea (validi)
    - 1 kielen, jossa latitude on merkkijono (testaa, mitä koodi tekee)
    """
    data = [
        {"id": "finn1318", "iso639_3": "fin", "family": "Finnic",
         "latitude": 62.0, "longitude": 25.0},
        {"id": "esto1258", "iso639_3": "est", "family": "Finnic",
         "latitude": 58.5, "longitude": 25.0},
        {"id": "xxxx1234", "family": "Test"},
        {"id": "yyyy1234", "iso639_3": "finnish"},
        {"id": "zzzz1234", "iso639_3": "fi"},
        {"id": "aaaa1234", "iso639_3": None},
        {"id": "sami1234", "iso639_3": "sme", "family": "Sámi"},
        {"id": "edge1234", "iso639_3": "xxx", "family": "Test",
         "latitude": "not-a-number"},
    ]
    path = tmp_path / "languoids.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path
