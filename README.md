# Global Language Family Mapper (GLFM)

A modular, JSON-based language database and validation pipeline for over 7,900 languages (ISO 639-3), including Uralic/Finno-Ugric languages. Designed for RSS feeds, localization, and NLP workflows.

* **Author:** Tuomas Lähteenmäki
* **License:** MIT
* **Version:** 1.0.2

---

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-success)
![Platform](https://img.shields.io/badge/Platform-Cross--platform-lightgrey)

---

## Features

* **7,900+ Languages:** Unified from ISO 639-1/2/3/5, Wiktionary, CLDR, Glottolog, and POS statistics.
* **Nearest Language Neighbors:** Each written language includes typologically nearest languages based on URIEL/lang2vec features (syntax, phonology, inventory, family).
* **Accurate BCP-47 Tags:** Language, script, and region combined automatically.
* **Fallback Chains:** Automatically assigns fallback languages where applicable.
* **Uralic/Finno-Ugric Support:** Detailed mapping for Finnish, Karelian, Estonian, and related languages.
* **Validation Pipeline:** Full automated checks for ISO consistency, BCP-47 compliance, fallback correctness, POS stats, and Glottolog data.
* **Graphviz Visualization:** Fallback relationships can be visualized.
* **Checkpoint/Resume Support:** Long-running nearest-language computations can be resumed automatically from a checkpoint.

---

## Directory Structure

```text
├── build_unified.py                # Build unified JSON database
├── data/                           # Raw and processed language data
│   ├── cldr/
│   │   └── likelySubtags.json
│   ├── iso_639_*.py                # ISO datasets in Python format
│   ├── override_scripts.json
│   ├── uralic_languages.json
│   └── ...
├── loaders/                        # Data loading modules
├── logic/                          # Logic for scripts, regions, fallbacks, BCP-47
├── models/                         # Data models (Language class, ISO modules)
├── output/                         # Pipeline output
│   ├── unified/                    # unified_languages.json
│   ├── validation/                 # validation reports, errors, fallback graph
│   ├── final/
│   ├── dialects/
│   └── logs/
├── tools/                          # Validation, report generation, and helpers
│   ├── compute_nearest_languages.py  # Compute nearest language neighbors
│   └── ...
├── run_full_pipeline.py            # Run full pipeline: build → validate → report
└── init.py
```

---

## Data Structure (`unified_languages.json`)

Each language is represented as a JSON object keyed by its ISO 639-3 code:

```json
"fin": {
  "id": "fin",
  "name": "Finnish",
  "official_name": "Finnish",
  "iso639_1": "fi",
  "iso639_2B": "fin",
  "iso639_2T": "fin",
  "iso639_3": "fin",
  "iso639_5": "",
  "default_script": "Latn",
  "default_region": "FI",
  "bcp47": "fi-Latn-FI",
  "fallback": "fin",
  "uralicNLP": true,
  "written": true,
  "written_scripts": ["Latn"],
  "glottocode": "finn1318",
  "family": "Uralic",
  "glottolog": {...},
  "pos_stats": {...},
  "nearest_languages": [
    {"lang": "est", "distance": 0.15},
    {"lang": "krl", "distance": 0.22},
    {"lang": "vep", "distance": 0.28}
  ],
  "distance_source": "lang2vec / URIEL",
  "distance_type": "fam",
  "distance_bases": ["WALS", "SSWL", "PHOIBLE", "Ethnologue", "Glottolog"]
}
```

- `bcp47` is automatically generated: `lang[-Script][-Region]`.
- `fallback` is the default fallback language.
- `uralicNLP` is true if the language belongs to the Uralic/Finno-Ugric family.
- `written_scripts` lists all known writing scripts.
- `nearest_languages` ranks typologically nearest written languages by distance (0.0 = identical features, 1.0 = completely different).

---

## Pipeline Overview

The pipeline is fully automated:

1. **Generate ISO files** (`tools/generate_iso_files.py`)
2. **Build Unified Database** (`build_unified.py`)
3. **Compute Nearest Languages** (`tools/compute_nearest_languages.py`) – adds `nearest_languages` field to all written languages (supports checkpoint/resume for long runs)
4. **Validate**:
   - BCP-47 tags (`validate_bcp47.py`)
   - Fallback chains (`validate_fallbacks.py`)
   - ISO consistency (`validate_iso_consistency.py`)
   - POS statistics (`validate_pos_stats.py`)
   - Glottolog data (`validate_glottolog.py`)
5. **Generate Validation Reports** (`generate_report.py`):
   - Markdown report (`validation_report.md`)
   - HTML report (`validation_report.html`)
   - JSON error log (`validation_errors.json`)
6. **Visualize Fallback Graph** (`visualize_fallbacks.py`)

---

## Requirements

* Python 3.8+
* Core dependencies: 'numpy>=1.26.0,<2.0.0', 'setuptools>=69.0.0'
* Language data: 'lang2vec>=1.1.0'
* Data processing: 'requests>=2.28.0'
* Visualization (optional): 'graphviz>=0.20.0'
* Testing (optional): 'pytest>=7.0.0'

---

## Usage

### Run the full pipeline

```bash
clone https://codeberg.org/lahtis/GLFM.git
pip install -r requirements.txt

python3 run_full_pipeline.py
```

Run nearest-language step manually

```bash
python3 tools/compute_nearest_languages.py
```

Note: Checkpoints are saved automatically to output/unified/nearest_languages.checkpoint.json and allow interrupted runs to resume seamlessly.

---

### Access data in Python

```python
import json
from pathlib import Path

unified_file = Path("output/unified/unified_languages.json")
with unified_file.open("r", encoding="utf-8") as f:
    languages = json.load(f)

# Access Finnish
finnish = languages.get("fin")
print(finnish["bcp47"])         # fi-Latn-FI
print(finnish["uralicNLP"])     # True
print(finnish["nearest_languages"][:5]) # Top 5 nearest languages
```

### Find nearest languages

```python
# Get 10 nearest languages to Finnish
finnish = languages.get("fin", {})
for neighbor in finnish.get("nearest_languages", [])[:10]:
    print(f"{neighbor['lang']}: {neighbor['distance']:.4f}")
```

## Notes

- `uralic_languages.json` must be present for Uralic support; the pipeline will warn if missing.
- The unified database integrates ISO, Wiktionary, CLDR, Glottolog, and POS stats.
- Fallback chains ensure robust language detection for RSS feeds and software localization.
- `nearest_languages` s computed using URIEL/lang2vec typological features (family, syntax, phonology, inventory).
- Distance scores range from `0.0` (identical features) to `1.0` (completely different).

---

## License

Copyright © 2026 Tuomas Lähteenmäki

This project is licensed under the MIT License. You may use, modify, and distribute the data, provided the original copyright notice is retained.

See LICENSE for details.
