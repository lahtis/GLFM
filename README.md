# Global Language Family Mapper (GLFM)

A JSON language database and validation pipeline covering 6,554 languages
in the consumer dataset and 7,928 in the research dataset, with extra
coverage of Uralic languages. The core has no dependencies; an optional
extra enables nearest-language computation. Built for RSS feeds,
localization, and NLP workflows.

- **Author:** Tuomas Lähteenmäki  
- **License:** MIT  

> See [CHANGELOG.md](CHANGELOG.md) for details.

---

[![PyPI](https://img.shields.io/pypi/v/glfm)](https://pypi.org/project/glfm/)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green) 
![Status](https://img.shields.io/badge/Status-Active-success)
[![Downloads](https://static.pepy.tech/badge/glfm)](https://pepy.tech/project/glfm)

---

## Primary Links

- [Canonical Repository (Codeberg)](https://codeberg.org/lahtis/GLFM)
- [GitHub Mirror](https://github.com/lahtis/GLFM)

---

## Features

- **6,554–7,928 Languages:** Consumer and research datasets are consolidated from ISO 639-1/2/3, Glottolog, CLDR, and other language metadata.
- **ISO 639-5 Family and Group Codes:** The full pipeline loads the LOC ISO 639-5 code list and maps languages through their Glottolog classification lineage.
- **Audit Reports:** Markdown and HTML reports include code-list membership, ISO 639-5 coverage, Glottolog source selection, metadata checks, and lineage coverage.
- **Nearest Language Neighbors:** Languages covered by URIEL include typologically nearest languages based on lang2vec features (syntax, phonology, inventory, family).
- **Accurate BCP-47 Tags:** Language, script, and region combined automatically.  
- **Fallback Chains:** Automatically assigns fallback languages where applicable.  
- **Uralic (including Finno-Ugric) Support:** Detailed mapping for Finnish, Karelian, Estonian, and related languages.
- **Validation Pipeline:** Full automated checks for ISO consistency, BCP-47 compliance, fallback correctness, POS stats, and Glottolog data.  
- **Checkpoint/Resume Support:** Long-running nearest-language computations can be resumed automatically from a checkpoint.  
- **Config Versioning:** `config.toml` carries a `config_version` key, separate from the package version.  
- **Optional POS Statistics:** Compute POS statistics from Wiktextract (~3 GB) with `--with-pos`.

---

## Directory Structure
```text
GLFM/
├── pyproject.toml
├── config.toml                    # Default configuration
├── README.md
├── LICENSE
├── CHANGELOG.md                   # Version history
├── VENDORED.md 
├── output/                        # Pipeline outputs (.gitignore)
│   ├── unified/                   # unified_languages.json, languages_top20.json.gz
│   ├── validation/                # validation_report.md/html, errors
│   └── logs/
├── src/
│   └── glfm/
│       ├── __init__.py
│       ├── _version.py
│       ├── paths.py               # Cache and data paths
│       ├── config.py              # Configuration
│       ├── download.py            # Data downloading
│       ├── build_unified.py       # Unified database builder
│       ├── run_full_pipeline.py   # Full pipeline
│       ├── data/                  # Internal data (packaged)
│       │   ├── override_scripts.json
│       │   └── uralic_languages.json
│       ├── utils/                 # Vendored safe HTTP layer
│       ├── loaders/               # Data source loaders
│       ├── logic/                 # Logic (script, region, fallback, BCP-47)
│       ├── models/                # Data models (Language)
│       └── tools/                 # Validators, reports, helper scripts
│           ├── build_pos_stats.py        # POS statistics (optional)
│           └── download_wiktextract.py   # Wiktextract download (~3 GB)
```

> Note: Downloadable data (`iso_639_*.py`, `glottolog.json`, `cldr/`) lives in the cache (`~/.cache/glfm/data/`), not in the repo. Bundled data (`override_scripts.json`, `uralic_languages.json`) is shipped with the package (`src/glfm/data/`).

> `download` is **not** part of the default pipeline.
> - `download`: use `python3 -m glfm.download --tier consumer|research` separately.
> - POS statistics are optional; use `--with-pos` (requires ~3 GB raw data).

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
  "family": "Uralic",
  "glottocode": "finn1318",
  "glottolog": {  },
  "id": "fin",
  "iso639_1": "fi",
  "iso639_2B": "fin",
  "iso639_2T": "fin",
  "iso639_3": "fin",
  "iso639_5": "urj",
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
- `family` is the Glottolog top-level family name (e.g. "Uralic"), not an ISO 639-5 code.
- `glottocode` is Glottolog language code (e.g. "finn1318").
- `iso639_5` is an ISO 639-5 family/group code when the Glottolog lineage
  maps to one (e.g. `urj` for Uralic); it is empty when the data has no
  unambiguous match.

### ISO 639-5 family and group assignment

The pipeline downloads the 115-code ISO 639-5 list from the Library of
Congress and Glottolog's compact Newick classification tree plus its
languoid catalogue. For each language, GLFM checks its Glottocode and then
walks up the Glottolog lineage, choosing the nearest matching ISO 639-5
group. The full Glottolog repository archive is not downloaded. If either
Glottolog data file cannot be fetched, the pipeline falls back to Wikidata
metadata, which may not include a lineage.

The assignment is necessarily partial: ISO 639-5 contains collection codes,
not a code for every Glottolog family or language. Unmapped languages keep
an empty `iso639_5` value. In a full-pipeline run on 2026-11-21, GLFM
assigned a code to 5,311 of 7,928 languages.

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
- Choose the research neighbor count with `--max-neighbors N` when running
  the full pipeline or the compute command. The default is 100; the consumer
  dataset keeps at most its configured top-20 entries. You can also set
  `max_neighbors` under `[nearest]` in `config.toml`.
- The computation still compares every eligible language pair to find the
  nearest neighbors. `max_neighbors` controls how many results are stored;
  `--matrix-chunk-size` controls how much of the distance matrix is in memory.
- `distance_6` is a 6-decimal version of `distance`. Use it for precise sorting,
  since 4-decimal values may tie.

---

## Pipeline Overview

The pipeline is fully automated:

generate ISO → build glottolog → build unified → compute nearest → build consumer → validate → report → visualize

| Step | Module | Description |
| :---- | :---- | :---- |
| generate | `glfm.tools.generate_iso_files` | Download ISO 639 sources |
| glottolog | `glfm.tools.build_glottolog_json` | Load Glottolog tree and catalogue (Wikidata fallback) |
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

### Full pipeline
```bash
python3 -m glfm.run_full_pipeline
```
### Choose how many nearest languages to store
```bash
python3 -m glfm.run_full_pipeline --max-neighbors 50
```
The default is 100 for the research dataset. Set `max_neighbors = 50` under
`[nearest]` in `config.toml` to make this the default for future runs. For a
direct compute run, use:
```bash
python3 -m glfm.tools.compute_nearest_languages --max-neighbors 50
```
### Include POS statistics (requires ~3 GB raw Wiktextract data)
```bash
python3 -m glfm.run_full_pipeline --with-pos
```
### List steps (add --with-pos to include pos_stats)
```bash
python3 -m glfm.run_full_pipeline --list
python3 -m glfm.run_full_pipeline --list --with-pos
```
### Skip nearest-language computation
```bash
python3 -m glfm.run_full_pipeline --skip compute
```
### Run only selected steps
```bash
python3 -m glfm.run_full_pipeline --only build bcp47
```
### Show help
```bash
python3 -m glfm.run_full_pipeline --help
```

---

## Configuration

Defaults are built into the package. Users can add overrides in
`~/.config/glfm/config.toml` (or the XDG config directory) and through
environment variables:

- `~/.config/glfm/config.toml`  
- Environment variables: `GLFM_CACHE_DIR`, `GLFM_DATA_DIR`, `GLFM_ISO_639_3_URL`, etc.

Example:
```toml
config_version = 7

[sources.iso_639_3]

url = "https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3.tab"

[sources.cldr]

version  = "48.0.0"

[sources.wikidata]

endpoint = "https://query.wikidata.org/sparql"

[sources.glottolog]
tree_url = "https://zenodo.org/records/24104033/files/tree_glottolog_newick.txt?download=1"
csv_url = "https://zenodo.org/records/24104033/files/glottolog_languoid.csv.zip?download=1"

[sources.wiktextract]
url = "https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz"
filename = "raw-wiktextract-data.jsonl.gz"
timeout = 3600

[paths]

data_dir = ""        # empty  =  ~/.cache/glfm/data

cache_dir = ""       # empty  =  ~/.cache/glfm
```

- **Download hashes:** SHA-256 verification is off by default. If an old
  config causes a hash mismatch, clear `sha256` under `[download.consumer]`
  or `[download.research]`. See the [changelog](CHANGELOG.md#notes).
---

## Quick Start

### 1. Install
```bash
pip install glfm
```

### 2. Get data

Choose one of these options. Downloading a prebuilt dataset does not
require the optional `data` extra.

Option A: Download pre-built data (recommended)
```bash
python3 -m glfm.download                    # consumer (654.4 kB)
python3 -m glfm.download --tier research    # research (1.9 MB)
```
Option B: Generate data from sources (slow, requires network)
```bash
pip install "glfm[data]"
python3 -m glfm.run_full_pipeline --only generate glottolog
```


### 3. (Optional) Generate or rebuild the datasets

Nearest-language computation requires the `data` extra. It calculates
pairwise distances in row chunks instead of keeping the full distance
matrix in memory. Reduce the chunk size on memory-limited machines; progress
is checkpointed so an interrupted run can resume:

```bash
python3 -m glfm.run_full_pipeline --matrix-chunk-size 16 --checkpoint-interval 100
```
`--matrix-chunk-size` defaults to 128 rows. Smaller values reduce peak
distance-matrix memory. `--checkpoint-interval` defaults to 1000 languages;
smaller values save progress more often. Both options are also available
when running `glfm.tools.compute_nearest_languages` directly.
### 4. Access data in Python

```python
import gzip, json
from pathlib import Path

cache = Path.home() / ".cache" / "glfm" / "data"
with gzip.open(cache / "languages_top20.json.gz", "rt") as f:
    languages = json.load(f)

fin = languages["fin"]
print(fin["bcp47"])                  # fi-Latn-FI
print(fin["family"])                 # Finnic
print(fin["glottocode"])             # finn1318
print(fin["nearest_languages"][:5])  # Top 5 nearest languages
```

### 5. Consumer dataset (top-20 neighbors)
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


POS statistics require ~3 GB of raw Wiktextract data. They are **not**
part of the default pipeline.

1. Download the Wiktextract dump:

```bash
python3 -m glfm.tools.download_wiktextract
```

2. Compute POS statistics:
```bash
python3 -m glfm.tools.build_pos_stats
```
    
3. Run the pipeline with POS data included:
```bash
python3 -m glfm.run_full_pipeline --with-pos
```

Without POS data, `pos_stats` is an empty `{}` for each language.

---



## Requirements

- **Python 3.11+** (tested through Python 3.14.7)
- **Core dependencies:** none (pure stdlib)  
- **Data extra:** `numpy`, `requests`, `msgpack`, `graphviz`, `lang2vec`
- **Development extra:** `pytest`, `pytest-cov`, `ruff`, `mypy`, `build`, `twine`

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

# Optional: dependencies for data generation and nearest-language computation
pip install -e ".[data]"
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

- **Glottolog:** Hammarström, Harald & Forkel, Robert & Haspelmath, Martin & Bank, Sebastian. [Glottolog 5.4](https://glottolog.org/download) – classification tree and languoid catalogue; Wikidata is the fallback source.
- **ISO 639-5:** [Library of Congress code list](https://id.loc.gov/vocabulary/iso639-5.html) and [official language coding agency](https://www.loc.gov/standards/iso639-5/).
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
