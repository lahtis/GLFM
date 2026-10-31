# Changelog

All notable changes to GLFM will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [1.0.7] — 2026-10-31

This release introduces configurable distance computation, optional POS
statistics, and a new config versioning scheme. The default distance
type changed from `fam` to `syntax_knn`, and nearest-language data now
includes a 6-decimal distance field.

### Added

#### Distance computation

- **`distance_6`** — a 6-decimal version of `distance` for each neighbor.
  The original `distance` (4 decimals) is kept for backward compatibility.
  `distance_6` allows precise sorting, since 4-decimal values may tie.
- **`distance_decimals`** — a new per-language field listing the stored
  decimal precisions, currently `[4, 6]`.
- **`_DISTANCE_BASES_MAP`** — maps each `distance_type` to the data sources
  it uses (e.g. `syntax_knn` → `["WALS", "SSWL", "Ethnologue"]`).
- **`_distance_bases_for(distance_type)`** — returns the correct
  `distance_bases` list for a given distance type. Unknown types fall back
  to the full default list.
- **`--distance-type`** — new CLI flag for `compute_nearest_languages.py`.
- **`decimals`** and **`checkpoint_interval`** — now parameters of
  `build_nearest_map()` and `run()` in `compute_nearest_languages.py`.

#### POS statistics (optional)

- **`glfm.tools.download_wiktextract`** — new module for streaming the
  Wiktextract dump (~5–10 GB) to the cache. Uses 1 MB chunks, logs
  progress every 100 MB, and computes SHA256 during download.
- **`glfm.tools.compute_pos_stats`** — new module for computing POS
  statistics from the Wiktextract dump. Produces `pos_stats.json`.
- **`--with-pos`** — new flag for `run_full_pipeline.py` that inserts
  the POS computation step before validation.

#### Configuration

- **`config_version`** — new top-level key in `config.toml` and
  `DEFAULT_CONFIG`. Tracks the config structure version (not the package
  version). Bumped to `2` in this release.
- **`CONFIG_VERSION`** — new constant in `config.py`.
- **`_check_config_version()`** — new function that warns if
  `config.toml` is older or newer than the current config version.
- **`[nearest]` section** in `config.toml`:
  - `distance_type` (default: `syntax_knn`)
  - `max_neighbors` (default: `100`)
  - `decimals` (default: `[4, 6]`)
  - `checkpoint_interval` (default: `1000`)
- **`[sources.wiktextract]` section** in `config.toml`:
  - `url` (Wiktextract dump URL)
  - `filename` (default: `raw-wiktextract-data.jsonl.gz`)
  - `timeout` (default: `3600`)
- **New environment variables**:
  - `GLFM_NEAREST_DISTANCE_TYPE`
  - `GLFM_NEAREST_MAX_NEIGHBORS`
  - `GLFM_NEAREST_DECIMALS`
  - `GLFM_NEAREST_CHECKPOINT_INTERVAL`
  - `GLFM_WIKTEXTTRACT_URL`
  - `GLFM_WIKTEXTTRACT_FILENAME`
  - `GLFM_WIKTEXTTRACT_TIMEOUT`
- **`_parse_env_value()`** — new function in `config.py` that parses
  environment variables into typed values (int, list of ints, or str).

#### Pipeline

- **Dynamic `--help`** for `run_full_pipeline.py` — the `epilog` is now
  built from `STEPS` and `POS_STEP`, so it stays in sync automatically.
- **`--list`** now shows the full step list, including `pos_stats` when
  `--with-pos` is given.
- **`--only` error message** now lists all available step keys when no
  match is found.

### Changed

#### Defaults

- **Default `distance_type` changed** from `fam` to `syntax_knn`.
  `fam` grouped all languages in the same family with identical distances;
  `syntax_knn` gives more meaningful typological neighbors.
- **`config.toml` download URLs** updated from `v1.0.5` to `v1.0.7`.
- **`config.py` download URLs** updated from `v1.0.5` to `v1.0.7`.
- **User-Agent** now built from `__version__` in `config.py` — not
  hardcoded in `config.toml`.

#### `compute_nearest_languages.py`

- **`MAX_NEIGHBORS`**, **`DISTANCE_TYPE`**, **`DISTANCE_DECIMALS`**, and
  **`CHECKPOINT_INTERVAL`** are no longer hardcoded. They are read from
  `config["nearest"]` in `main()` and passed as parameters to
  `build_nearest_map()`, `attach_metadata()`, and `run()`.
- **`compute_distance_matrix()`** now takes `distance_type` as a parameter
  instead of using a global constant.
- **`attach_metadata()`** now takes `distance_type` and `decimals` as
  parameters.
- **`run()`** now takes `distance_type`, `decimals`, and
  `checkpoint_interval` as parameters.
- **Comments** translated from Finnish to English.

#### `build_consumer_dataset.py`

- **`filter_neighbors()`** now copies all neighbor fields with `dict(n)`
  instead of rebuilding `{"lang": ..., "distance": ...}`. This preserves
  `distance_6` and any future fields.
- **`_neighbor_distance()`** — new helper that prefers `distance_6` over
  `distance` when sorting or filtering.

#### `compute_pos_stats.py`

- **`_get_lang_code()`** — new helper that validates the language code
  from `lang_code` (not `lang`, which is a language name).
- **`used` counter** — now logs how many lines were actually used
  (had both `lang_code` and `pos`).
- **Log messages and comments** translated from Finnish to English.

#### `run_full_pipeline.py`

- **`download` step removed** from the default pipeline. It was redundant
  because the pipeline builds the data itself. Use
  `python3 -m glfm.download --tier consumer|research` separately.
- **`pos_stats` step removed** from the default pipeline. It requires
  5–10 GB of raw data and is now opt-in via `--with-pos`.
- **Comments** translated from Finnish to English.

#### `download_wiktextract.py`

- **All hardcoded values removed** — URL, filename, and timeout are read
  from `config["sources"]["wiktextract"]`.
- **New CLI flags**: `--output`, `--timeout`.
- **`--url` default** now comes from config, not a constant.

### Fixed

- **`syntax_average` no longer produces empty neighbor lists.** The
  `'--'` missing values were converted to `NaN`, which propagated through
  the matrix product and made every distance `NaN`. `syntax_knn` is now
  the default because it fills missing values via KNN prediction.
- **`distance_type` was not passed to `build_nearest_map()`** — it used
  a global constant, so changing `config.toml` had no effect. Fixed by
  passing it as a parameter.
- **`build_consumer_dataset.py` dropped `distance_6`** when filtering
  neighbors. Fixed by copying the full neighbor dict.
- **`download` step in `run_full_pipeline.py` was redundant** — it
  downloaded a pre-built dataset that the pipeline then overwrote. Removed
  from the default pipeline.

### Removed

- **`download` step** from the default `run_full_pipeline.py` pipeline.
  Still available as a standalone command:
  `python3 -m glfm.download --tier consumer|research`.
- **`pos_stats` step** from the default pipeline. Now opt-in via
  `--with-pos`.
- **`sys` import** from `download_wiktextract.py` (unused).

### Documentation

- **README.md** rewritten:
  - Added **Data Structure** example with `syntax_knn`, `distance_6`,
    `distance_decimals`, and correct `distance_bases`.
  - Added **Distance types and their use cases** table (`fam`,
    `syntax_knn`, `phonology_knn`, `inventory_knn`, `geo`, `learned`).
  - Added **Recommendation by use case** (localization, RSS, NLP).
  - Added **`distance_bases`** table showing which sources each
    `distance_type` uses.
  - Added **Coverage limitations** section (3,709 / 7,205 languages in
    URIEL; 3,030 living written languages with 0 neighbors).
  - Added **`distance_6`** section explaining precise sorting.
  - Added **Installation** split into user (PyPI) and developer (source)
    paths.
  - Added **Optional: POS statistics** section.
  - Added **`language_type`** note: `L` follows ISO 639-3, but some
    languages classified as `L` may have no native speakers (e.g. Yokuts).
  - Updated **Key changes** table with rows 11–14.
- **`config.toml`** — all comments translated to English; new sections
  `[nearest]` and `[sources.wiktextract]`; `config_version = 2`.
- **`config.py`** — all comments and docstrings translated to English;
  `CONFIG_VERSION = 2`; `_check_config_version()`.

### Internal

- **`_DISTANCE_BASES_MAP`** and **`_DEFAULT_DISTANCE_BASES`** moved to
  module level in `compute_nearest_languages.py` (were inline).
- **`GLFM_VERSION` fallback** updated from `1.0.5` to `1.0.7`.
- **`CheckpointManager`** now stores `distance_type` and `glfm_version`,
  so checkpoints are invalidated when either changes.

---

## [1.0.6] — (unreleased)

Intermediate version. Superseded by 1.0.7.

---

## [1.0.5] — (previous release)

Initial public release with `fam`-based nearest languages, top-20 consumer
dataset, and validation pipeline.
