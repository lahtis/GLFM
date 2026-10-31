# Vendored code

This file documents code that has been copied from another project
(SHL) into GLFM. Vendored code is kept in sync manually.

**Rule:** fix upstream first (in SHL), then re-vendor here.
Do not edit vendored files directly unless the change is
GLFM-specific — in that case, document it below.

---

## `src/glfm/utils/safe_http_common.py`

- **Source:** `shl/utils/safe_http_common.py` @ v0.3.0
- **Upstream:** https://codeberg.org/lahtis/SHL/blob/main/shl/utils/safe_http_common.py
- **Synced:** 2026-10-31
- **Modifications:**
  - `from shl._version import __version__` → `from glfm._version import __version__`
  - `SHL_USER_AGENT` → `GLFM_USER_AGENT` (value changed to GLFM URL)
  - Docstring: SHL-specific references (`shl.engine.errors.parser`,
    SHL error code mappings) replaced with GLFM-neutral descriptions
  - `kind` documentation updated to list GLFM's known kinds

---

## `src/glfm/utils/safe_http.py`

- **Source:** `shl/utils/safe_http.py` @ v0.3.0
- **Upstream:** https://codeberg.org/lahtis/SHL/blob/main/shl/utils/safe_http.py
- **Synced:** 2026-10-31
- **Modifications:**
  - `SHL_USER_AGENT` → `GLFM_USER_AGENT` (import and usage)
  - `safe_http_post()` removed (GLFM uses GET only for SPARQL)
  - Docstring: SHL-specific references removed

---

## `src/glfm/utils/__init__.py`

- **Source:** GLFM-specific (not vendored)
- **Purpose:** re-exports the public API of `safe_http_common` and
  `safe_http` so callers can use `from glfm.utils import ...`

---

## Notes

### Why vendor instead of depending on SHL?

GLFM follows a pure-stdlib policy (`dependencies = []`). Adding SHL
as a runtime dependency would:

- introduce a dependency chain (SHL → its own dependencies)
- require version resolution between GLFM and SHL
- break the "no external dependencies" guarantee

Vendoring keeps the code local, auditable, and dependency-free.

### Why not copy SHL's tests?

SHL's 67 tests for the safe HTTP layer are extensive. Copying them
would create two test suites that drift apart. Instead:

- SHL tests the upstream code (67 tests + kind-protocol guard)
- GLFM tests only its own divergences (see
  `tests/utils/test_safe_http_glfm.py`)

This keeps the test surface small and focused.

### When to re-vendor

Re-vendor from SHL when:

- SHL fixes a security issue in `safe_http_common.py` or `safe_http.py`
- SHL adds a new `kind` value that GLFM should handle
- SHL changes the public API (e.g. `safe_urlopen` signature)

After re-vendoring:

1. Re-apply the GLFM-specific modifications listed above
2. Update the `Synced:` date
3. Run `pytest tests/` to verify nothing broke
4. Run `python3 -m glfm.run_full_pipeline --skip pos_stats` to verify
   the pipeline still works

### Known limitation — DNS rebinding

`safe_http.py` documents a known limitation: the hostname is resolved
once for validation and then again by urllib for the actual connection.
This is accepted because endpoints are hard-coded in the source (or
read from a trusted `config.toml`).

If endpoints become configurable from untrusted input, this limitation
must be addressed by pinning the resolved IP to the connection while
preserving the original hostname for TLS and HTTP.
