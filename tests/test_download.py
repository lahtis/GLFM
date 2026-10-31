# tests/test_download.py

def test_download_rejects_unknown_tier():
    from glfm.download import download_data
    with pytest.raises(ValueError):
        download_data(tier="unknown")

def test_download_uses_safe_urlopen(monkeypatch):
    """Varmistaa, että safe_urlopen:ia käytetään (ei urllib suoraan)."""
    called = {}
    def fake_safe_urlopen(url, timeout):
        called["url"] = url
        called["timeout"] = timeout
        raise SafeHTTPError("stop", kind="transport")
    monkeypatch.setattr("glfm.download.safe_urlopen", fake_safe_urlopen)
    with pytest.raises(RuntimeError):
        download_data(tier="consumer")
    assert "url" in called

def test_download_warns_when_sha256_missing(monkeypatch, caplog):
    """Jos sha256 puuttuu, varoitus näkyy lokissa."""
    # ...mock safe_urlopen palauttamaan dataa, config ilman sha256:ta
    # ...tarkista caplog:sta "No SHA256 configured"

def test_download_verifies_sha256(monkeypatch):
    """Jos sha256 on asetettu ja väärä, RuntimeError."""
    # ...

def test_marker_requires_file(monkeypatch, tmp_path):
    """Jos marker on mutta tiedosto puuttuu, ladataan uudelleen."""
    # ...
