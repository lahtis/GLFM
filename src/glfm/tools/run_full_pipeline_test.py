#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.1.0
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
# Smoke test: runs build + validators + visualization and reports
# whether everything passed. Does NOT replace run_full_pipeline.py.
#

import argparse
import logging
import subprocess
import sys
import time

log = logging.getLogger(__name__)

# (key, title, module, timeout)
STEPS = [
    (
        "build",
        "Build unified_languages.json",
        "glfm.build_unified",
        600,
    ),
    (
        "bcp47",
        "Validate BCP-47 tags",
        "glfm.tools.validate_bcp47",
        120,
    ),
    (
        "fallbacks",
        "Validate fallback chains",
        "glfm.tools.validate_fallbacks",
        120,
    ),
    (
        "iso",
        "Validate ISO consistency",
        "glfm.tools.validate_iso_consistency",
        120,
    ),
    (
        "viz",
        "Visualize fallback graph",
        "glfm.tools.visualize_fallbacks",
        120,
    ),
]


def run_module(
    module: str,
    title: str,
    timeout: int,
) -> tuple[bool, float]:
    """Run a module. Returns (ok, elapsed_seconds)."""
    print(f"\n=== {title} ===")
    print(f"Running: python3 -m {module}")

    t0 = time.time()
    try:
        result = subprocess.run(
            [sys.executable, "-m", module],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] {timeout}s")
        return False, time.time() - t0
    except FileNotFoundError:
        print(f"[ERROR] Module not found: {module}")
        return False, time.time() - t0

    elapsed = time.time() - t0

    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print("stderr:", result.stderr.strip())

    if result.returncode != 0:
        print(f"[FAILED] {title} ({elapsed:.1f}s)")
        return False, elapsed

    print(f"[OK] {title} ({elapsed:.1f}s)")
    return True, elapsed


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Smoke test: build + validators + visualization."
        ),
    )
    parser.add_argument(
        "--skip", nargs="*", default=[],
        help=(
            "Skip these steps (keys: "
            + ", ".join(k for k, *_ in STEPS) + ")"
        ),
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    steps = [s for s in STEPS if s[0] not in args.skip]
    if not steps:
        log.error("All steps skipped — nothing to run.")
        return 1

    print("========================================")
    print(" FULL PIPELINE TEST")
    print("========================================")
    print(f"Steps: {', '.join(s[0] for s in steps)}")

    all_ok = True
    total = 0.0
    failures: list[str] = []

    for key, title, module, timeout in steps:
        ok, elapsed = run_module(module, title, timeout)
        total += elapsed
        if not ok:
            all_ok = False
            failures.append(key)

    print("\n========================================")
    if all_ok:
        print(f" ALL TESTS PASSED ({total:.1f}s)")
    else:
        print(f" SOME TESTS FAILED ({total:.1f}s)")
        print(f"   Failed: {', '.join(failures)}")
    print("========================================")

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
