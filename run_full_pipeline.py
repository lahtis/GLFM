#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Global Language Family Mapper (GLFM)
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.0.2
#
# https://codeberg.org/lahtis/GLFM
#
# Licensed under the MIT License.
# You may obtain a copy of the License at:
# https://opensource.org/licenses/MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
TOOLS = PROJECT_ROOT / "tools"

# Pipeline steps
GENERATE_ISO_FILES = TOOLS / "generate_iso_files.py"
BUILD_UNIFIED = PROJECT_ROOT / "build_unified.py"
COMPUTE_NEAREST = TOOLS / "compute_nearest_languages.py"
VALIDATE_BCP47 = TOOLS / "validate_bcp47.py"
VALIDATE_FALLBACKS = TOOLS / "validate_fallbacks.py"
VALIDATE_ISO = TOOLS / "validate_iso_consistency.py"
VALIDATE_POS = TOOLS / "validate_pos_stats.py"
VALIDATE_GLOTTO = TOOLS / "validate_glottolog.py"
GENERATE_REPORT = TOOLS / "generate_report.py"
VISUALIZE_FALLBACKS = TOOLS / "visualize_fallbacks.py"


def run(title: str, script: Path) -> bool:
    print(f"\n=== {title} ===")
    print(f"Running: {script}\n")

    # Inherit stdout and stderr to display logs directly in real time
    process = subprocess.Popen([sys.executable, str(script)])
    process.wait()

    if process.returncode != 0:
        print(f"\n[FAILED] {title} (Exit code: {process.returncode})")
        return False

    print(f"\n[OK] {title}")
    return True


def main():
    print("========================================")
    print(" FULL PIPELINE EXECUTION")
    print("========================================")

    steps = [
        ("Generate ISO files", GENERATE_ISO_FILES),
        ("Build unified database", BUILD_UNIFIED),
        ("Compute nearest languages (lang2vec)", COMPUTE_NEAREST),
        ("Validate BCP-47 tags", VALIDATE_BCP47),
        ("Validate fallback chains", VALIDATE_FALLBACKS),
        ("Validate ISO consistency", VALIDATE_ISO),
        ("Validate POS statistics", VALIDATE_POS),
        ("Validate Glottolog data", VALIDATE_GLOTTO),
        ("Generate validation report", GENERATE_REPORT),
        ("Generate fallback graph (Graphviz)", VISUALIZE_FALLBACKS),
    ]

    all_ok = True

    for title, script in steps:
        if not script.exists():
            print(f"\n[ERROR] Script not found at {script}")
            all_ok = False
            break

        ok = run(title, script)
        if not ok:
            all_ok = False
            break  # Stop pipeline immediately on error

    print("\n========================================")
    if all_ok:
        print(" FULL PIPELINE COMPLETED SUCCESSFULLY")
        print(" Reports and graphs are in output/validation/")
    else:
        print(" PIPELINE COMPLETED WITH ERRORS")
        print(" Check the logs above for details.")
    print("========================================")


if __name__ == "__main__":
    main()