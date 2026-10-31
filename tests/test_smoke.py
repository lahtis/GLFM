# tests/test_smoke.py
"""Smoke test: package imports without errors."""


def test_import_glfm() -> None:
    import glfm
    assert glfm.__name__ == "glfm"


def test_import_version() -> None:
    from glfm._version import __version__
    assert isinstance(__version__, str)
    assert __version__
