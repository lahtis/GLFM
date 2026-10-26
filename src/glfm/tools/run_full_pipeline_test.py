#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.0.2
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
# Smoke test: ajaa build + validaattorit + visualisoinnin ja kertoo
# menikö kaikki läpi. EI korvaa run_full_pipeline.py:tä.
#

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

from glfm.paths import get_data_dir, get_output_dir

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS = PROJECT_ROOT / "tools"
OUTPUT = get_output_dir()

# (avain, otsikko, skripti, timeout)
STEPS = [
    ("build", "Build unified_languages.json",
     PROJECT_ROOT / "build_unified.py", 600),
    ("bcp47", "Validate BCP-47 tags",
     TOOLS / "validate_bcp47.py", 120),
    ("fallbacks", "Validate fallback chains",
     TOOLS / "validate_fallbacks.py", 120),
    ("iso", "Validate ISO consistency",
     TOOLS / "validate_iso_consistency.py", 120),
    ("viz", "Visualize fallback graph",
     TOOLS / "visualize_fallbacks.py", 120),
]


def run_script(path: Path, title: str, timeout: int) -> tuple[bool, float]:
    """Ajaa skriptin. Palauttaa (ok, kesto_sekunteina)."""
    print(f"\n=== {title} ===")
    print(f"Running: {path}")

    t0 = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"⏱ TIMEOUT ({timeout}s)")
        return False, time.time() - t0
    except FileNotFoundError:
        print(f"✘ Skriptiä ei ole: {path}")
        return False, time.time() - t0

    elapsed = time.time() - t0

    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print("stderr:", result.stderr.strip())

    if result.returncode != 0:
        print(f"✘ {title} FAILED ({elapsed:.1f}s)")
        return False, elapsed

    print(f"✔ {title} OK ({elapsed:.1f}s)")
    return True, elapsed


def main():
    parser = argparse.ArgumentParser(
        description="Smoke test: build + validaattorit + visualisointi.",
    )
    parser.add_argument(
        "--skip", nargs="*", default=[],
        help="Ohita nämä vaiheet (avaimet: " +
             ", ".join(k for k, *_ in STEPS) + ")",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    steps = [s for s in STEPS if s[0] not in args.skip]
    if not steps:
        log.error("Kaikki vaiheet ohitettu – ei ajettavaa.")
        return 1

    print("========================================")
    print(" FULL PIPELINE TEST")
    print("========================================")
    print(f"Vaiheet: {', '.join(s[0] for s in steps)}")

    all_ok = True
    total = 0.0
    failures: list[str] = []

    for key, title, script, timeout in steps:
        ok, elapsed = run_script(script, title, timeout)
        total += elapsed
        if not ok:
            all_ok = False
            failures.append(key)

    print("\n========================================")
    if all_ok:
        print(f" ALL TESTS PASSED ({total:.1f}s)")
    else:
        print(f" SOME TESTS FAILED ({total:.1f}s)")
        print(f"   Epäonnistuivat: {', '.join(failures)}")
    print("========================================")

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
