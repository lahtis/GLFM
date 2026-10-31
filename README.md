# Global Language Family Mapper (GLFM)

A modular, JSON-based language database and validation pipeline for over 7,900 languages (ISO 639-3), including Uralic/Finno-Ugric languages. Designed for RSS feeds, localization, and NLP workflows.

- **Author:** Tuomas Lähteenmäki  
- **License:** MIT  
- **Version:** 1.0.7

> **Beta:** GLFM is in beta. The data format and config structure may change before 1.0.0 stable. See [CHANGELOG.md](CHANGELOG.md) for details.

---

[![PyPI](https://img.shields.io/pypi/v/glfm)](https://pypi.org/project/glfm/)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green) 
![Status](https://img.shields.io/badge/Status-Active-success)
![Status](https://img.shields.io/badge/Status-Beta-yellow)
[![Downloads](https://static.pepy.tech/badge/glfm)](https://pepy.tech/project/glfm)

---

## Primary Links

- Canonical Repository (Codeberg): `https://codeberg.org/lahtis/GLFM`  
- GitHub Mirror: `https://github.com/lahtis/GLFM`

---

## Features

## Features

- **7,900+ Languages:** Unified from ISO 639-1/2/3/5, Wikidata (Glottolog), CLDR, and POS statistics.  
- **Nearest Language Neighbors:** Each written language includes typologically nearest languages based on URIEL/lang2vec features (syntax, phonology, inventory, family).  
- **Accurate BCP-47 Tags:** Language, script, and region combined automatically.  
- **Fallback Chains:** Automatically assigns fallback languages where applicable.  
- **Uralic/Finno-Ugric Support:** Detailed mapping for Finnish, Karelian, Estonian, and related languages.  
- **Validation Pipeline:** Full automated checks for ISO consistency, BCP-47 compliance, fallback correctness, POS stats, and Glottolog data.  
- **Checkpoint/Resume Support:** Long-running nearest-language computations can be resumed automatically from a checkpoint.  
- **Config Versioning:** `config.toml` carries a `config_version` key, separate from the package version.  
- **Optional POS Statistics:** Compute POS statistics from Wiktextract (5–10 GB) with `--with-pos`.

---

## Directory Structure
```text
GLFM/
├── pyproject.toml
├── config.toml                    # Default configuration
├── README.md
├── LICENCE
├── CHANGELOG.md                   # Version history
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
│           ├── compute_pos_stats.py       # POS statistics (optional)
│           ├── download_wiktextract.py    # Wiktextract download (5-10 GB)
└── venv/
```

> Note: Downloadable data (`iso_639_*.py`, `glottolog.json`, `cldr/`) lives in the cache (`~/.cache/glfm/data/`), not in the repo. Bundled data (`override_scripts.json`, `uralic_languages.json`) is shipped with the package (`src/glfm/data/`).

> `download` and `pos_stats` are **not** part of the default pipeline.
> - `download`: use `python3 -m glfm.download --tier consumer|research` separately.
> - `pos_stats`: use `--with-pos` (requires 5–10 GB raw data).

---

## Data Structure (`unified_languages.json`)

Each language is represented as a JSON object keyed by its ISO 639-3 code:
```json
"fin": {
  "bcp47": "fi-Latn-FI",
  "default_region": "FI",
  "default_script": "Latn",
  "distance_bases": ["WALS", "SSWL", "Ethnologue"],
  "distance_decimals": [4, 6],
  "distance_source": "lang2vec / URIEL",
  "distance_type": "syntax_knn",
  "fallback": "fin",
  "family": "Finnic",
  "glottocode": "finn1318",
  "glottolog": {  },
  "id": "fin",
  "iso639_1": "fi",
  "iso639_2B": "fin",
  "iso639_2T": "fin",
  "iso639_3": "fin",
  "iso639_5": "",
  "language_type": "L",
  "name": "Finnish",
  "nearest_languages": [
    {"lang": "izh", "distance": 0.0097, "distance_6": 0.009709},
    {"lang": "vep", "distance": 0.0097, "distance_6": 0.009709},
    ...
  ],
  "official_name": "Finnish",
  "pos_stats": {},
  "uralicNLP": true,
  "written": true,
  "written_scripts": ["Latn"]
}
```
> The example above is abbreviated for readability. The full JSON contains
> up to 20 neighbors (consumer) or 100 neighbors (research) per language.
> See `languages_top20.json.gz` and `unified_languages.json.gz` for the complete data.


- `bcp47` is automatically generated: `lang[-Script][-Region]`.
- `fallback` is the default fallback language.
- `uralicNLP` is true if the language belongs to the Uralic/Finno-Ugric family.
- `written_scripts` lists all known writing scripts.
- `language_type` is SIL Language Type (L = Living, E = Extinct, H = Historical, A = Ancient, C = Constructed).
  Note: `L` follows ISO 639-3 classification; some languages classified as `L` may have no native speakers (e.g. Yokuts).
- `family` is Glottolog family name (e.g. "Finnic"), not an ISO 639-5 code.
- `glottocode` is Glottolog language code (e.g. "finn1318").

**Distance fields:**

- `distance_type` is the distance method used (`syntax_knn` by default as of v1.0.7).
  See the table below for available methods and their use cases.
- `distance_source` is the upstream source of the distance computation (`lang2vec / URIEL`).
- `distance_bases` lists the data sources used for the distance calculation.
  The value depends on `distance_type` (see the table below).
- `distance_decimals` lists the decimal precisions stored in `nearest_languages`.
  Currently `[4, 6]`: `distance` (4 decimals) and `distance_6` (6 decimals).
- `nearest_languages` ranks typologically nearest written languages by distance
  (up to `max_neighbors`, default 100 for research, 20 for consumer).
  Each entry contains `lang`, `distance` (4 decimals), and `distance_6` (6 decimals).
- `distance_6` is a 6-decimal version of `distance`. Use it for precise sorting,
  since 4-decimal values may tie.

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
# Include POS statistics (requires 5-10 GB raw Wiktextract data)
```bash
python3 -m glfm.run_full_pipeline --with-pos
```
# List steps (add --with-pos to include pos_stats)
```bash
python3 -m glfm.run_full_pipeline --list
python3 -m glfm.run_full_pipeline --list --with-pos
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
# Show help
```bash
python3 -m glfm.run_full_pipeline --help
```

---

## Configuration

`config.toml` (repo root) contains default values. Users can override:

- `~/.config/glfm/config.toml`  
- Environment variables: `GLFM_DATA_DIR`, `GLFM_CACHE_DIR`, `GLFM_OUTPUT_DIR`, `GLFM_ISO_639_3_URL`, etc.

Example:
```toml
config_version = 2

[sources.iso_639_3]

url = "https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3.tab"

[sources.cldr]

version  = "48.0.0"

[sources.wikidata]

endpoint = "https://query.wikidata.org/sparql"

[sources.wiktextract]
url = "https://dumps.wikimedia.org/other/wiktextract/20260101/wiktextract-data.jsonl.gz"
filename = "raw-wiktextract-data.jsonl.gz"
timeout = 3600

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

### 5 . Consumer dataset (top-20 neighbors)
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

### 6. Research dataset (up to 100 neighbors)

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

### 7. Optional: POS statistics


POS statistics require 5–10 GB of raw Wiktextract data. They are **not**
part of the default pipeline.

1. Download the Wiktextract dump:

```bash
python3 -m glfm.tools.download_wiktextract
```

2. Compute POS statistics:
```bash
python3 -m glfm.tools.compute_pos_stats
```
    
3. Run the pipeline with POS data included:
```bash
python3 -m glfm.run_full_pipeline --with-pos
```

Without POS data, pos_stats is an empty {} for each language.

---



## Requirements

- **Python 3.9+**  
- **Core dependencies:** none (pure stdlib)  
- **Dev dependencies:** `numpy`, `requests`, `msgpack`, `lang2vec`, `graphviz`, `pytest`

## Installation

### 1. For users (PyPI)
If you only need the package and pre-built data:
```bash
pip install glfm
```
Then download the data (see Quick Start).

---

### 2. For developers (from source)

```bash
git clone https://codeberg.org/lahtis/GLFM.git
cd GLFM
python3 -m venv venv
source venv/bin/activate    # Linux/macOS
# venv\Scripts\activate     # Windows

# Install package in editable mode
pip install -e .

# Install development dependencies (optional)
pip install -e ".[dev]"
```
> Note: pip install glfm installs the published PyPI version.
> pip install -e . installs the local repository in editable mode.
> Do not mix them in the same environment unless you know what you are doing 

---

## Distance types and their use cases

GLFM provides nearest-language data using different distance types.
The `distance_type` field in each language entry tells which one was used.

| `distance_type` | Measures | Best for | Limitations |
|---|---|---|---|
| `fam` | Language family (Glottolog) | Family relationships, historical linguistics | Identical values for all languages in the same family; poor for isolates |
| `syntax_knn` | Syntactic similarity (WALS, SSWL, Ethnologue) | NLP transfer learning, typological comparison | Does not reflect cultural or geographic proximity |
| `phonology_knn` | Phonological similarity (WALS, PHOIBLE) | Speech technology, pronunciation modeling | Limited to languages in PHOIBLE |
| `inventory_knn` | Sound inventory (PHOIBLE) | Phoneme-level NLP | Limited coverage |
| `geo` | Geographic distance (Glottolog) | Localization, regional grouping | Not a linguistic measure |
| `learned` | Learned embeddings (Malaviya et al.) | General-purpose similarity | Requires more computation |

**Recommendation by use case:**

- **Localization:** Use `fam` or `geo` for cultural/regional proximity. `syntax_knn` may mislead (e.g. Estonian ranks 8th for Finnish).
- **RSS:** Use `fallback` chains (already provided). `nearest_languages` is supplementary.
- **NLP:** Use `syntax_knn` or `learned` for transfer learning and multilingual models.

---

## `distance_bases`

Lists the data sources used for the distance calculation.
The value depends on `distance_type`:

| `distance_type` | `distance_bases` |
|---|---|
| `fam` | `["Glottolog"]` |
| `syntax_knn` | `["WALS", "SSWL", "Ethnologue"]` |
| `phonology_knn` | `["WALS", "PHOIBLE", "Ethnologue"]` |
| `inventory_knn` | `["PHOIBLE", "Ethnologue"]` |
| `learned` | `["WALS", "SSWL", "PHOIBLE", "Ethnologue", "Glottolog"]` |
| `syntax_average` | `["WALS", "SSWL", "Ethnologue"]` (may produce `NaN` due to missing values; prefer `syntax_knn`) |

---

## Coverage limitations

URIEL (the underlying database) covers 3,709 of the 7,205 written languages in GLFM.
Languages not in URIEL receive an empty `nearest_languages` list.

As of the current release:
- 7,205 written languages total
- 3,709 have URIEL feature vectors
- 3,030 living written languages have 0 neighbors, because:
  - the language is not in URIEL (3,496 written languages total are missing from URIEL), OR
  - all neighbors were filtered out by `build_consumer_dataset.py` (e.g. neighbors are dead or unwritten).
  
This is a known limitation. If you need nearest-language data for a language not in URIEL,
consider using Glottolog-based family distance (`fam`) as a fallback.

---

## `distance_6`

A 6-decimal version of `distance`. Use it for precise sorting
(4-decimal values may tie) and for comparing distances across languages.

`distance` (4 decimals) is kept for backward compatibility.

---

## Data Sources & Acknowledgments

- **Glottolog:** Hammarström, Harald & Forkel, Robert & Haspelmath, Martin & Bank, Sebastian. Glottolog. (glottolog.org) – fetched via Wikidata SPARQL.  
- **URIEL / lang2vec:** Typological vector representations.  
- **ISO 639:** Language code standards (ISO 639-1, 639-2, 639-3, 639-5).  
- **CLDR / Wiktionary:** Locale display names, scripts.
- **Wiktextract:** Raw Wiktionary extracts for POS statistics (optional).

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
| 4 | `nearest_languages` | 5 → **20 (consumer) / 100 (research)** |
| 5 | Pipeline Overview | **12 steps** (incl. `glottolog`, `consumer`) |
| 6 | CLI | **`python3 -m glfm.run_full_pipeline`** |
| 7 | Configuration | **`config.toml`** + env vars |
| 8 | Requirements | **No core dependencies** (pure stdlib) |
| 9 | `build_top5.py` | **`build_consumer_dataset.py`** |
| 10 | "Glottolog future work" | **Glottolog works** (Wikidata) |
| 11 | `distance_type` default | `fam` → **`syntax_knn`** (as of v1.0.7) |
| 12 | `distance_6` | **New field** (6-decimal distance, for precise sorting) |
| 13 | `distance_decimals` | **New field** (`[4, 6]`, lists stored precisions) |
| 14 | `distance_bases` | **Now depends on `distance_type`** (e.g. `syntax_knn` → `["WALS", "SSWL", "Ethnologue"]`) |
| 15 | `distance_bases` table | **Added `syntax_average`** (may produce `NaN`; prefer `syntax_knn`) |
| 16 | `config_version` | **New key** in `config.toml` (tracks config structure, not package version) |
| 17 | `--with-pos` | **New CLI flag** for optional POS statistics (requires 5–10 GB) |
| 18 | `download_wiktextract` | **New module** for streaming the Wiktextract dump |
