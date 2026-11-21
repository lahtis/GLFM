**GLFM 1.2.0**

Language database for 7,928 languages (ISO 639-3), with a 6,554-language
consumer dataset and expanded ISO 639-5 and Glottolog metadata.

### Files

- `languages_top20.json.gz` (~1.1 MB) — consumer dataset, 6,554 languages,
  up to 20 nearest-language neighbors
- `unified_languages.json.gz` (~2.5 MB) — research dataset, 7,928 languages,
  up to 100 nearest-language neighbors

### Changes

- Assign ISO 639-5 family and group codes by following Glottolog language
  lineages; use Wikidata metadata when the Glottolog source is unavailable
- Add validation reports for ISO 639-5 registry membership, Glottolog
  metadata, source selection, and lineage coverage
- Compute nearest-language distances in bounded matrix chunks instead of
  allocating the full N×N matrix in memory; all language pairs are still
  compared, so this reduces memory use rather than total computation
- Add checkpoint and resume support for interrupted nearest-language runs;
  tune save frequency with `--checkpoint-interval`
- Add `--matrix-chunk-size` to control peak distance-matrix memory
- Add `--max-neighbors` to choose how many nearest languages to store per
  language; also configurable with `[nearest].max_neighbors`
- Add `[nearest].matrix_chunk_size` and
  `GLFM_NEAREST_MATRIX_CHUNK_SIZE`; bump `config_version` to 7
- Set default download SHA-256 values to empty; warn that older user configs
  may need their old `sha256` entries removed or cleared
- Pin `setuptools<80.9` in the `data` extra to avoid the `pkg_resources`
  deprecation warning from `lang2vec`

### Statistics

- `unified_languages.json.gz`: 7,928 languages; 370,900 nearest-language
  entries across 3,709 languages with URIEL features
- `languages_top20.json.gz`: 6,554 languages; 70,480 nearest-language
  entries across 3,524 languages with URIEL features
- ISO 639-5 registry: 115 codes; assigned to 5,311 research-dataset
  languages and 4,581 consumer-dataset languages

### Install

```bash
pip install glfm
python3 -m glfm.download
python3 -m glfm.download --tier research
```
