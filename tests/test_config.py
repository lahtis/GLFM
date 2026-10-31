# tests/test_config.py

def test_load_config_returns_deepcopy():
    from glfm.config import load_config, DEFAULT_CONFIG
    c1 = load_config()
    c2 = load_config()
    assert c1 is not c2
    assert c1["sources"] is not c2["sources"]

def test_env_override(monkeypatch):
    monkeypatch.setenv("GLFM_WIKIDATA_ENDPOINT", "https://example.com/sparql")
    from glfm.config import load_config
    c = load_config()
    assert c["sources"]["wikidata"]["endpoint"] == "https://example.com/sparql"

def test_env_decimals_parsed(monkeypatch):
    monkeypatch.setenv("GLFM_NEAREST_DECIMALS", "4,6")
    from glfm.config import load_config
    c = load_config()
    assert c["nearest"]["decimals"] == [4, 6]

def test_env_timeout_parsed(monkeypatch):
    monkeypatch.setenv("GLFM_HTTP_TIMEOUT", "30")
    from glfm.config import load_config
    c = load_config()
    assert c["http"]["timeout"] == 30

def test_config_version_is_current():
    from glfm.config import load_config, CONFIG_VERSION
    c = load_config()
    assert c["config_version"] == CONFIG_VERSION
