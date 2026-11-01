# tests/logic/test_is_uralic.py
"""Tests for is_uralic / set_uralic_langs."""

import pytest

from glfm.logic.is_uralic import is_uralic, set_uralic_langs


@pytest.fixture(autouse=True)
def reset_uralic_set():
    """Reset the global Uralic set before each test."""
    set_uralic_langs(None)
    yield
    set_uralic_langs(None)


class TestIsUralic:
    def test_empty_set(self) -> None:
        assert is_uralic("fin") is False

    def test_set_from_list(self) -> None:
        set_uralic_langs(["fin", "est", "sme"])
        assert is_uralic("fin") is True
        assert is_uralic("est") is True
        assert is_uralic("sme") is True
        assert is_uralic("eng") is False

    def test_set_from_set(self) -> None:
        set_uralic_langs({"fin", "hun"})
        assert is_uralic("fin") is True
        assert is_uralic("hun") is True

    def test_set_replaces_previous(self) -> None:
        set_uralic_langs(["fin"])
        set_uralic_langs(["est"])
        assert is_uralic("fin") is False
        assert is_uralic("est") is True

    def test_none_clears_set(self) -> None:
        set_uralic_langs(["fin"])
        set_uralic_langs(None)
        assert is_uralic("fin") is False

    def test_invalid_type_clears_set(self) -> None:
        set_uralic_langs(["fin"])
        set_uralic_langs(123)  # not iterable
        assert is_uralic("fin") is False
