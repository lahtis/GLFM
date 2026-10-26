# loaders/__init__.py
"""
GLFM – datalähteiden latausmoduulit.

Jokainen loaderi lukee yhden datalähteen ja palauttaa jäsennellyn dictin.
"""

__all__ = [
    "load_cldr_likely_subtags",
    "load_glottolog",
    "load_iso_639",
    "load_override_scripts",
    "load_pos_stats",
    "load_uralic_languages",
    "load_wiktionary_languages",
    "load_written_languages",
]

