# glfm/_version.py
"""
Yksi totuuden lähde versiolle.

Käyttö:
    from glfm._version import __version__
    from glfm._version import __version_tuple__

Versio noudattaa PEP 440 -standardia:
    MAJOR.MINOR.PATCH[.devN | .aN | .bN | .rcN]
"""

__version__ = "1.0.5"
__version_tuple__ = tuple(int(x) for x in __version__.split(".")[:3])

# Valinnainen: git-commit, build-päivä (voi päivittää CI:ssä)
__build_date__ = "2026-10-27"
__git_commit__ = "unknown"
