# __init__.py
"""
GLFM – Global Language Family Mapper

Kielimetatietokanta ja -työkalut 7900+ kielelle (ISO 639-3).

Yksi totuuden lähde versiolle: _version.py
"""

try:
    from _version import __version__, __version_tuple__
except ImportError:
    try:
        from glfm._version import __version__, __version_tuple__
    except ImportError:
        __version__ = "1.0.4"
        __version_tuple__ = (1, 0, 4)

__all__ = ["__version__", "__version_tuple__"]
