# Global Language Family Mapper (GLFM)

A modular, JSON-based language database and validation pipeline for over 7,900 languages (ISO 639-3), including Uralic/Finno-Ugric languages. Designed for RSS feeds, localization, and NLP workflows.

- **Author:** Tuomas Lähteenmäki  
- **License:** MIT  
- **Version:** 1.0.6

---

[![PyPI](https://img.shields.io/pypi/v/glfm)](https://pypi.org/project/glfm/)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue) 
![License](https://img.shields.io/badge/License-MIT-green) 
![Status](https://img.shields.io/badge/Status-Active-success)
[![Downloads](https://static.pepy.tech/badge/glfm)](https://pepy.tech/project/glfm)

---

## Primary Links

- Canonical Repository (Codeberg): `https://codeberg.org/lahtis/GLFM`  
- GitHub Mirror: `https://github.com/lahtis/GLFM`

---

## Features

- **7,900+ Languages:** Unified from ISO 639-1/2/3/5, Wikidata (Glottolog), CLDR, and POS statistics.  
- **Nearest Language Neighbors:** Each written language includes typologically nearest languages based on URIEL/lang2vec features (syntax, phonology, inventory, family).  
- **Accurate BCP-47 Tags:** Language, script, and region combined automatically.  
- **Fallback Chains:** Automatically assigns fallback languages where applicable.  
- **Uralic/Finno-Ugric Support:** Detailed mapping for Finnish, Karelian, Estonian, and related languages.  
- **Validation Pipeline:** Full automated checks for ISO consistency, BCP-47 compliance, fallback correctness, POS stats, and Glottolog data.  
- **Checkpoint/Resume Support:** Long-running nearest-language computations can be resumed automatically from a checkpoint.

---

## Directory Structure
```text
GLFM/
├── pyproject.toml
├── config.toml                    # Default configuration
├── README.md
├── LICENCE
├── output/                        # Pipeline outputs (.gitignore)
│   ├── unified/                   # unified_languages.json, languages_top20.json.gz
│   ├── validation/                # validation_report.md/html, errors
│   └── logs/
├── src/
│   └── glfm/
│       ├── __init__.py
│       ├── _version.py
│       ├── paths.py               # Paths (cache, data, output)
│       ├── config.py              # Configuration
│       ├── download.py            # Data downloading
│       ├── build_unified.py       # Unified database builder
│       ├── run_full_pipeline.py   # Full pipeline
│       ├── data/                  # Internal data (packaged)
│       │   ├── override_scripts.json
│       │   └── uralic_languages.json
│       ├── loaders/               # Data source loaders
│       ├── logic/                 # Logic (script, region, fallback, BCP-47)
│       ├── models/                # Data models (Language)
│       └── tools/                 # Validators, reports, helper scripts
└── venv/
```

> Note: Downloadable data (`iso_639_*.py`, `glottolog.json`, `cldr/`) lives in the cache (`~/.cache/glfm/data/`), not in the repo. Bundled data (`override_scripts.json`, `uralic_languages.json`) is shipped with the package (`src/glfm/data/`).

---

## Data Structure (`unified_languages.json`)

Each language is represented as a JSON object keyed by its ISO 639-3 code:
```json
"fin": {
  "bcp47": "fi-Latn-FI",
  "default_region": "FI",
  "default_script": "Latn",
  "distance_bases":  [
    "WALS",
    "SSWL",
    "PHOIBLE",
    "Ethnologue",
    "Glottolog"
   ],
  "distance_source": "lang2vec / URIEL",
  "distance_type": "fam",
  "fallback": "fin",
  "family": "Finnic",
  "glottocode": "finn1318",
  "glottolog": {
    "glottocode": "finn1318",
    "iso639_3": "fin",
    "family": "Finnic",
    "macroarea": "",
    "latitude": 62.0,
    "longitude": 25.0,
    "lineage":  [ ],
    "status": ""
  },
  "id": "fin",
  "iso639_1": "fi",
  "iso639_2B": "fin",
  "iso639_2T": "fin",
  "iso639_3": "fin",
  "iso639_5": "",
  "language_type": "L",
  "name": "Finnish",
  "nearest_languages":  [
    {
      "lang": "est",
      "distance": 0.0003
    },
    {
      "lang": "izh",
      "distance": 0.0003
    }
   ],
  "official_name": "Finnish",
  "pos _stats": {},
  "uralicNLP": true,
  "written": true,
  "written_scripts":  [
    "Latn"
   ]
}
```

- `bcp47` is automatically generated: `lang[-Script][-Region]`.  
- `fallback` is the default fallback language.  
- `uralicNLP` is true if the language belongs to the Uralic/Finno-Ugric family.  
- `written_scripts` lists all known writing scripts.  
- `nearest_languages` ranks typologically nearest written languages by distance (up to 100 max_neighbors).  
- `language_type` is SIL Language Type (L = Living, E = Extinct, H = Historical, A = Ancient, C = Constructed).  
- `family` is Glottolog family name (e.g. "Finnic"), not an ISO 639-5 code.  
- `glottocode` is Glottolog language code (e.g. "finn1318").

---

## Pipeline Overview

The pipeline is fully automated:

generate ISO → build glottolog → build unified → compute nearest → build consumer → validate → report → visualize

| Step | Module | Description |
| :---- | :---- | :---- |
| generate | `glfm.tools.generate_iso_files` | Download ISO 639 sources |
| glottolog | `glfm.tools.build_glottolog_json` | Fetch Glottolog metadata (Wikidata) |
| build | `glfm.build_unified` | Build unified database |
| compute | `glfm.tools.compute_nearest_languages` | Compute neighbors (lang2vec) |
| consumer | `glfm.tools.build_consumer_dataset` | Build consumer dataset (top-20) |
| bcp47 | `glfm.tools.validate_bcp47` | Validate BCP-47 |
| fallbacks | `glfm.tools.validate_fallbacks` | Validate fallbacks |
| iso | `glfm.tools.validate_iso_consistency` | Validate ISO codes |
| pos | `glfm.tools.validate_pos_stats` | Validate POS statistics |
| glotto | `glfm.tools.validate_glottolog` | Validate Glottolog |
| report | `glfm.tools.generate_report` | Generate reports |
| viz | `glfm.tools.visualize_fallbacks` | Visualize fallbacks (optional) |

---

## CLI

# Full pipeline
```bash
python3 -m glfm.run_full_pipeline
```

# Skip heavy neighbor computation
```bash
python3 -m glfm.run_full_pipeline --skip compute
```

# Run only selected steps
```bash
python3 -m glfm.run_full_pipeline --only build bcp47
```

# List steps
```bash
python3 -m glfm.run_full_pipeline --list
```
---

## Configuration

`config.toml` (repo root) contains default values. Users can override:

- `~/.config/glfm/config.toml`  
- Environment variables: `GLFM_DATA_DIR`, `GLFM_CACHE_DIR`, `GLFM_OUTPUT_DIR`, `GLFM_ISO_639_3_URL`, etc.

Example:
```toml
[sources.iso_639_3]

url = "https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3.tab"

[sources.cldr]

version  = "48.0.0"

[sources.wikidata]

endpoint = "https://query.wikidata.org/sparql"

[paths]

data_dir = ""        # empty  =  ~/.cache/glfm/data

cache_dir = ""       # empty  =  ~/.cache/glfm
```
---

## Quick Start

### 1 . Install 
```bash
pip install glfm
```

### 2. Get data
Choose one of these:

Option A: Download pre-built data (recommended)
```bash
python3 -m glfm.download                    # consumer (558 kB)
python3 -m glfm.download --tier research    # research (1.4 MB)
```
Option B: Generate data from sources (slow, requires network)
```bash
python3 -m glfm.run_full_pipeline --only generate glottolog
```


### 3 . Run the full pipeline
```bash
python3 -m glfm.run_full_pipeline
```
### 4 . Access data in Python

```python
import gzip, json
from pathlib import Path

cache = Path.home() / ".cache" / "glfm" / "data"
with gzip.open(cache / "unified_languages.json.gz", "rt") as f:
    languages = json.load(f)

fin = languages["fin"]
print(fin["bcp47"])                  # fi-Latn-FI
print(fin["family"])                 # Finnic
print(fin["glottocode"])             # finn1318
print(fin["nearest_languages"][:5])  # Top 5 nearest languages
```

### 4 . Consumer dataset (top-20 neighbors)
```python
import gzip
import json
from pathlib import Path

cache = Path.home() / ".cache" / "glfm" / "data"
with gzip.open(cache / "languages_top20.json.gz", "rt") as f:
    languages = json.load(f)

fin = languages["fin"]
print(f"bcp47: {fin['bcp47']}")           # fi-Latn-FI
print(f"family: {fin['family']}")         # Finnic
print(f"glottocode: {fin['glottocode']}") # finn1318
print(f"language_type: {fin['language_type']}")  # L
print(f"neighbors: {len(fin['nearest_languages'])}")  # 20

for nb in fin["nearest_languages"]:
    print(f"{nb['lang']}: {nb['distance']:.4f}")
```

### 5. Research dataset (up to 100 neighbors)

```python
import gzip
import json
from pathlib import Path

# Option A: read from cache (after `glfm.download --tier research`)
cache = Path.home() / ".cache" / "glfm" / "data"
# Option B: read from pipeline output (after `glfm.run_full_pipeline`)
# output = Path("output/unified")

with gzip.open(cache / "unified_languages.json.gz", "rt") as f:
    languages = json.load(f)

fin = languages["fin"]
print(f"neighbors: {len(fin['nearest_languages'])}")  # 100

for nb in fin["nearest_languages"]:
    print(f"{nb['lang']}: {nb['distance']:.4f}")
```

---

## Requirements

- **Python 3.9+**  
- **Core dependencies:** none (pure stdlib)  
- **Dev dependencies:** `numpy`, `requests`, `msgpack`, `lang2vec`, `graphviz`, `pytest`

## Installation

### 1. Create virtual environment

```bash
git clone https://codeberg.org/lahtis/GLFM.git
cd GLFM
python3 -m venv venv
source venv/bin/activate    # Linux/macOS
# venv\Scripts\activate     # Windows
```

### 2. Install package
```bash
pip install glfm
```
### 3. Install development dependencies (optional)
```bash
pip install -e ".[dev]"
```
or 

```bash
git clone https://codeberg.org/lahtis/GLFM.git
cd GLFM
python3 -m venv venv
source venv/bin/activate
pip install -e .
```
---

## Data Sources & Acknowledgments

- **Glottolog:** Hammarström, Harald & Forkel, Robert & Haspelmath, Martin & Bank, Sebastian. Glottolog. (glottolog.org) – fetched via Wikidata SPARQL.  
- **URIEL / lang2vec:** Typological vector representations.  
- **ISO 639:** Language code standards (ISO 639-1, 639-2, 639-3, 639-5).  
- **CLDR / Wiktionary:** Locale display names, scripts.

---

## Contributing & Issues

[https://codeberg.org/lahtis/GLFM](https://codeberg.org/lahtis/GLFM)

---

## License

Copyright © 2026 Tuomas Lähteenmäki  
MIT License. See LICENSE for details.

---

## Key changes

|  # | Section | Change |
| :---- | :---- | :---- |
| 1 | Python version | `3.8+` → **`3.9+`** |
| 2 | Directory Structure | **`src/glfm/` layout** |
| 3 | Data Structure | **`family: "Finnic"`**, `glottocode: "finn1318"`, `language_type: "L"` |
| 4 | `nearest_languages` | 5 → **100** (max) |
| 5 | Pipeline Overview | **12 steps** (incl. `glottolog`, `consumer`) |
| 6 | CLI | **`python3 -m glfm.run_full_pipeline`** |
| 7 | Configuration | **`config.toml`**  + env vars |
| 8 | Requirements | **No core dependencies** (pure stdlib) |
| 9 | `build_top5.py` | **`build_consumer_dataset.py`** |
| 10 | "Glottolog future work" | **Glottolog works** (Wikidata) |

