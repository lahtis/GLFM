# logic/__init__.py
"""
GLFM – logiikkamoduulit.

Skriptien, alueiden, fallbackien ja BCP-47:n päätöslogiikka.
"""

__all__ = [
    "build_bcp47",
    "build_extinct_json",
    "decide_default_region",
    "decide_default_script",
    "decide_fallback",
    "is_uralic",
    "resolve_cldr_key",
    "set_uralic_langs",
]
