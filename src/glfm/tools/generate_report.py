#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.1.1
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
# Run validators and generate a unified pipeline report
# (Markdown + HTML + JSON).
#

import html
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from glfm.errors import DataError, OperationalError
from glfm.loaders.load_iso_639 import load_iso_639_5
from glfm.paths import get_bundled_data_dir, get_data_dir

log = logging.getLogger(__name__)

TOOLS = Path(__file__).resolve().parent

VALIDATORS = {
    "bcp47": TOOLS / "validate_bcp47.py",
    "fallbacks": TOOLS / "validate_fallbacks.py",
    "iso": TOOLS / "validate_iso_consistency.py",
    "glottolog": TOOLS / "validate_glottolog.py",
}


def summarize_audit(data: dict, iso639_5_code_count: int) -> dict:
    """Summarize ISO 639-5 assignment and Glottolog lineage coverage."""
    total = len(data)
    assigned = sum(
        bool(info.get("iso639_5"))
        for info in data.values()
        if isinstance(info, dict)
    )
    with_glottocode = sum(
        bool(info.get("glottocode"))
        for info in data.values()
        if isinstance(info, dict)
    )
    with_lineage = sum(
        bool((info.get("glottolog") or {}).get("lineage"))
        for info in data.values()
        if isinstance(info, dict)
        and isinstance(info.get("glottolog"), dict)
    )
    return {
        "total_languages": total,
        "iso639_5_assigned": assigned,
        "iso639_5_unassigned": total - assigned,
        "iso639_5_coverage_percent": round(assigned * 100 / total, 1)
        if total else 0.0,
        "iso639_5_registry_codes": iso639_5_code_count,
        "glottocode_records": with_glottocode,
        "lineage_records": with_lineage,
    }


def _atomic_write_text(path: Path, content: str) -> None:
    """Atomic text write."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)
    except OSError as e:
        raise OperationalError(
            f"Could not write {path}: {e}",
            source="filesystem",
            kind="transport",
        ) from e


def _atomic_write_json(path: Path, data: dict) -> None:
    """Atomic JSON write."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)
    except OSError as e:
        raise OperationalError(
            f"Could not write {path}: {e}",
            source="filesystem",
            kind="transport",
        ) from e


def run_validation(script: Path, timeout: int = 120) -> tuple[str, str, int]:
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", f"Timeout ({timeout}s)", 124
    except FileNotFoundError:
        return "", f"Script not found: {script}", 127


def _clean_output(stdout: str, ok_markers: list[str]) -> list[str]:
    if not stdout:
        return []
    for marker in ok_markers:
        if marker in stdout:
            return []
    return stdout.splitlines()


def _validator_errors(result: dict, ok_markers: list[str]) -> list[str]:
    errors = _clean_output(result["stdout"], ok_markers)
    if result["returncode"] and not errors:
        errors = [
            result["stderr"]
            or f"Validator exited with status {result['returncode']}"
        ]
    return errors


def generate_report() -> None:
    output_root = get_data_dir()
    output_root.mkdir(parents=True, exist_ok=True)

    unified = output_root / "unified_languages.json"
    glottolog_source_path = output_root / "glottolog_source.json"
    validation_errors_json = (
        output_root / "validation" / "validation_errors.json"
    )
    # uralic_languages.json is bundled with the package, not in the
    # data directory.
    uralic_file = get_bundled_data_dir() / "uralic_languages.json"

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )

    uralic_warning = None
    if not uralic_file.exists() or uralic_file.stat().st_size == 0:
        uralic_warning = (
            "Warning: uralic_languages.json missing or empty. "
            "All languages will have uralicNLP=False"
        )

    results: dict = {}
    for key, script in VALIDATORS.items():
        log.info("Running: %s", script.name)
        stdout, stderr, rc = run_validation(script)
        results[key] = {
            "stdout": stdout,
            "stderr": stderr,
            "returncode": rc,
        }

    iso_errors = _validator_errors(
        results["iso"],
        ["All ISO codes are valid"],
    )
    iso639_5_errors = [
        error
        for error in iso_errors
        if "iso639_5" in error or "ISO 639-5" in error
    ]
    errors_json = {
        "bcp47": _validator_errors(
            results["bcp47"],
            ["BCP-47 validation OK"],
        ),
        "bcp47_stderr": (
            results["bcp47"]["stderr"].splitlines()
            if results["bcp47"]["stderr"] else []
        ),
        "fallbacks": _validator_errors(
            results["fallbacks"],
            ["All fallback chains are valid"],
        ),
        "fallbacks_stderr": (
            results["fallbacks"]["stderr"].splitlines()
            if results["fallbacks"]["stderr"] else []
        ),
        "iso": [
            error
            for error in iso_errors
            if "iso639_5" not in error and "ISO 639-5" not in error
        ],
        "iso639_5_codes": iso639_5_errors,
        "iso_stderr": (
            results["iso"]["stderr"].splitlines()
            if results["iso"]["stderr"] else []
        ),
        "glottolog": _validator_errors(
            results["glottolog"],
            ["Glottolog validation OK"],
        ),
        "glottolog_stderr": (
            results["glottolog"]["stderr"].splitlines()
            if results["glottolog"]["stderr"] else []
        ),
        "returncodes": {
            k: v["returncode"] for k, v in results.items()
        },
    }

    lang_count = 0
    unified_data = {}
    if unified.exists():
        try:
            with open(unified, "r", encoding="utf-8") as f:
                unified_data = json.load(f)
                if isinstance(unified_data, dict):
                    lang_count = len(unified_data)
                else:
                    unified_data = {}
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Could not read %s: %s", unified, e)
    else:
        log.warning("unified_languages.json missing: %s", unified)

    glottolog_source = {"source": "not_recorded"}
    if glottolog_source_path.exists():
        try:
            with glottolog_source_path.open("r", encoding="utf-8") as f:
                loaded_source = json.load(f)
            if isinstance(loaded_source, dict):
                glottolog_source = loaded_source
            else:
                glottolog_source = {"source": "invalid_metadata"}
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Could not read Glottolog source metadata: %s", exc)
            glottolog_source = {"source": "invalid_metadata"}

    audit_summary = summarize_audit(
        unified_data,
        len(load_iso_639_5()),
    )
    audit_summary["glottolog_source"] = glottolog_source
    errors_json["audit_summary"] = audit_summary
    _atomic_write_json(validation_errors_json, errors_json)

    def status(key: str) -> str:
        return "OK" if not errors_json[key] else "Errors found"

    md = f"""# Unified Pipeline Report
**Generated:** {timestamp}

## Summary
- Total languages: **{lang_count}**
- BCP‑47 validation: {status("bcp47")}
- Fallback validation: {status("fallbacks")}
- ISO validation: {status("iso")}
- ISO 639-5 registry check: {status("iso639_5_codes")}
- Glottolog validation: {status("glottolog")}
- Glottolog source: **{glottolog_source.get("source", "unknown")}**
- Glottolog source records: **{glottolog_source.get("record_count", "unknown")}**; source lineages: **{glottolog_source.get("lineage_count", "unknown")}**
- ISO 639-5 assignment: **{audit_summary["iso639_5_assigned"]}/{lang_count}** ({audit_summary["iso639_5_coverage_percent"]}%)
- ISO 639-5 registry codes: **{audit_summary["iso639_5_registry_codes"]}**
- Glottocode records: **{audit_summary["glottocode_records"]}/{lang_count}**; lineages: **{audit_summary["lineage_records"]}/{lang_count}**
"""
    if uralic_warning:
        md += f"\n**{uralic_warning}**\n"

    md += "\n---\n"
    for key, title in [
        ("bcp47", "BCP‑47"),
        ("fallbacks", "Fallback"),
        ("iso", "ISO"),
        ("glottolog", "Glottolog"),
    ]:
        out = results[key]["stdout"] or "No output"
        err = results[key]["stderr"]
        md += f"\n## {title} Validation Output\n{out}\n"
        if err:
            md += f"\n**stderr:**\n```\n{err}\n```\n"

    md += "\n---\n"
    md_path = output_root / "validation" / "validation_report.md"
    _atomic_write_text(md_path, md)

    def render_errors(title: str, error_list: list[str]) -> str:
        if not error_list:
            return (
                f"<h3>{html.escape(title)}</h3>"
                f"<p class='ok'>No errors.</p>"
            )
        rows = "".join(
            f"<tr><td>{html.escape(e)}</td></tr>" for e in error_list
        )
        return (
            f"<h3>{html.escape(title)}</h3>"
            f"<table border='1' cellpadding='5' cellspacing='0'>"
            f"<tr><th>Error</th></tr>{rows}</table>"
        )

    errors_html = ""
    errors_html += render_errors("BCP-47 Errors", errors_json["bcp47"])
    errors_html += render_errors(
        "Fallback Errors", errors_json["fallbacks"]
    )
    errors_html += render_errors("ISO Errors", errors_json["iso"])
    errors_html += render_errors(
        "ISO 639-5 Registry Errors", errors_json["iso639_5_codes"]
    )
    errors_html += render_errors("Glottolog Errors", errors_json["glottolog"])

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Unified Pipeline Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 40px; }}
pre {{ background: #f0f0f0; padding: 10px; border-radius: 6px; white-space: pre-wrap; }}
.ok {{ color: green; font-weight: bold; }}
.err {{ color: red; font-weight: bold; }}
table {{ border-collapse: collapse; margin-bottom: 20px; }}
th, td {{ border: 1px solid #ccc; padding: 5px; }}
</style>
</head>
<body>
<h1>Unified Pipeline Report</h1>
<p><strong>Generated:</strong> {timestamp}</p>

<h2>Summary</h2>
<ul>
  <li>Total languages: <strong>{lang_count}</strong></li>
  <li>BCP‑47 validation: <span class="{'ok' if not errors_json['bcp47'] else 'err'}">{status('bcp47')}</span></li>
  <li>Fallback validation: <span class="{'ok' if not errors_json['fallbacks'] else 'err'}">{status('fallbacks')}</span></li>
  <li>ISO validation: <span class="{'ok' if not errors_json['iso'] else 'err'}">{status('iso')}</span></li>
  <li>ISO 639-5 registry check: <span class="{'ok' if not errors_json['iso639_5_codes'] else 'err'}">{status('iso639_5_codes')}</span></li>
  <li>Glottolog validation: <span class="{'ok' if not errors_json['glottolog'] else 'err'}">{status('glottolog')}</span></li>
  <li>Glottolog source: <strong>{html.escape(str(glottolog_source.get('source', 'unknown')))}</strong>; source records: <strong>{glottolog_source.get('record_count', 'unknown')}</strong></li>
  <li>ISO 639-5 assignment: <strong>{audit_summary['iso639_5_assigned']}/{lang_count}</strong> ({audit_summary['iso639_5_coverage_percent']}%); registry codes: <strong>{audit_summary['iso639_5_registry_codes']}</strong></li>
  <li>Glottocode records: <strong>{audit_summary['glottocode_records']}/{lang_count}</strong>; lineages: <strong>{audit_summary['lineage_records']}/{lang_count}</strong></li>
</ul>
"""
    if uralic_warning:
        html_content += (
            f"<p style='color:red; font-weight:bold;'>"
            f"{html.escape(uralic_warning)}</p>\n"
        )

    for key, title in [
        ("bcp47", "BCP‑47"),
        ("fallbacks", "Fallback"),
        ("iso", "ISO"),
        ("glottolog", "Glottolog"),
    ]:
        out = results[key]["stdout"] or "No output"
        err = results[key]["stderr"]
        html_content += (
            f"<h2>{title} Validation Output</h2>\n"
            f"<pre>{html.escape(out)}"
        )
        if err:
            html_content += f"\n{html.escape(err)}"
        html_content += "</pre>\n"

    html_content += (
        f"<h2>Detailed Validation Errors</h2>\n"
        f"{errors_html}\n</body></html>"
    )

    html_path = output_root / "validation" / "validation_report.html"
    _atomic_write_text(html_path, html_content)

    log.info("Markdown: %s", md_path)
    log.info("HTML: %s", html_path)
    log.info("Errors JSON: %s", validation_errors_json)

    print()
    print(f"Languages: {lang_count}")
    print(f"BCP-47: {status('bcp47')}")
    print(f"Fallback: {status('fallbacks')}")
    print(f"ISO: {status('iso')}")
    print(f"Glottolog: {status('glottolog')}")
    print(
        "ISO 639-5: "
        f"{audit_summary['iso639_5_assigned']}/{lang_count} "
        f"({audit_summary['iso639_5_coverage_percent']}%)"
    )


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        generate_report()
    except OperationalError as exc:
        log.error("Source error: %s", exc)
        if exc.retryable:
            log.error("Error is temporary — try again later.")
        return 1
    except DataError as exc:
        log.error("Data error: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
