#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Global Language Family Mapper (GLFM)
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.0.4
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from glfm.paths import get_data_dir, get_output_dir

# run_full_pipeline.py on src/glfm/run_full_pipeline.py
# → parent = src/glfm/ → parent.parent = src/ → parent.parent.parent = repo root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT = get_output_dir()
LOG_DIR = OUTPUT / "logs"


# --- Vaiheiden määritelmä ---------------------------------------------------
# (avain, otsikko, moduuli, tyyppi)
#   tyyppi: "producer"  – pysäyttää pipelinein virheeseen
#           "validator" – jatkaa, kerää kaikki virheet
#           "optional"  – valinnainen, ei kaada pipelineä
STEPS = [
    ("generate",  "Generate ISO files",
     "glfm.tools.generate_iso_files", "producer"),
    ("glottolog", "Build Glottolog JSON",
     "glfm.tools.build_glottolog_json", "producer"),
    ("build",     "Build unified database",
     "glfm.build_unified", "producer"),
    ("compute",   "Compute nearest languages",
     "glfm.tools.compute_nearest_languages", "producer"),
    ("consumer",  "Build consumer dataset",
     "glfm.tools.build_consumer_dataset", "producer"),
    ("bcp47",     "Validate BCP-47 tags",
     "glfm.tools.validate_bcp47", "validator"),
    ("fallbacks", "Validate fallback chains",
     "glfm.tools.validate_fallbacks", "validator"),
    ("iso",       "Validate ISO consistency",
     "glfm.tools.validate_iso_consistency", "validator"),
    ("pos",       "Validate POS statistics",
     "glfm.tools.validate_pos_stats", "validator"),
    ("glotto",    "Validate Glottolog data",
     "glfm.tools.validate_glottolog", "validator"),
    ("report",    "Generate validation report",
     "glfm.tools.generate_report", "validator"),
    ("viz",       "Generate fallback graph",
     "glfm.tools.visualize_fallbacks", "optional"),
]

# Timeoutit sekunteina. None = ei timeouttia (pitkä ajo).
TIMEOUTS = {
    "compute": None,
    "build": 600,
    "generate": 300,
    "glottolog": 300,
    "consumer": 300,
}
DEFAULT_TIMEOUT = 300


def setup_logging():
    """Avaa lokitiedoston ja palauttaa Tee-olion."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"pipeline_{datetime.now():%Y%m%d_%H%M%S}.log"
    log_file = open(log_path, "w", encoding="utf-8")

    class Tee:
        def __init__(self, *streams):
            self.streams = streams

        def write(self, msg):
            for s in self.streams:
                s.write(msg)
                s.flush()

        def flush(self):
            for s in self.streams:
                s.flush()

    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = Tee(original_stdout, log_file)
    sys.stderr = Tee(original_stderr, log_file)
    return log_path


def run_step(title: str, module: str, timeout: int | None) -> bool:
    """Ajaa yhden vaiheen moduulina. Palauttaa True jos exit code == 0."""
    print(f"\n=== {title} ===")
    print(f"Module: {module}")
    if timeout:
        print(f"Timeout: {timeout}s")

    cmd = [sys.executable, "-m", module]

    try:
        process = subprocess.Popen(cmd)
    except OSError as e:
        print(f"[ERROR] {e}")
        return False

    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"\n[TIMEOUT] {title} ylitti {timeout}s – tapetaan.")
        process.kill()
        process.wait()
        return False
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Pipeline interrupted by user.")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        sys.exit(130)

    if process.returncode != 0:
        print(f"\n[FAILED] {title} (exit {process.returncode})")
        return False

    print(f"\n[OK] {title}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="GLFM full pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esimerkkejä:
  python3 -m glfm.run_full_pipeline                    # kaikki vaiheet
  python3 -m glfm.run_full_pipeline --skip compute     # ohita raskas naapurilaskenta
  python3 -m glfm.run_full_pipeline --only build bcp47 # aja vain valitut
  python3 -m glfm.run_full_pipeline --list             # listaa vaiheet
""",
    )
    parser.add_argument("--skip", nargs="*", default=[], metavar="KEY",
                        help="Ohita nämä vaiheet (avaimet: " +
                             ", ".join(k for k, *_ in STEPS) + ")")
    parser.add_argument("--only", nargs="*", default=[], metavar="KEY",
                        help="Aja vain nämä vaiheet")
    parser.add_argument("--list", action="store_true",
                        help="Listaa vaiheet ja lopeta")
    args = parser.parse_args()

    if args.list:
        for key, title, module, kind in STEPS:
            marker = {"producer": "[pakollinen]",
                      "validator": "[validaattori]",
                      "optional":  "[valinnainen]"}[kind]
            print(f"  {key:10s} {title:35s} {marker}")
        return

    if args.only:
        steps = [s for s in STEPS if s[0] in args.only]
        if not steps:
            print(f"[ERROR] --only ei tunnistanut yhtään avainta: {args.only}")
            sys.exit(1)
    else:
        steps = [s for s in STEPS if s[0] not in args.skip]

    log_path = setup_logging()
    print("========================================")
    print(" FULL PIPELINE EXECUTION")
    print("========================================")
    print(f"Log: {log_path}")
    print(f"Vaiheet: {', '.join(s[0] for s in steps)}")

    failed = []
    skipped = []

    for key, title, module, kind in steps:
        timeout = TIMEOUTS.get(key, DEFAULT_TIMEOUT)
        ok = run_step(title, module, timeout)

        if not ok:
            if kind == "producer":
                print(f"\n[STOP] Tuotantovaihe epäonnistui: {title}")
                failed.append((key, "failed"))
                break
            elif kind == "optional":
                print(f"\n[SKIP] Valinnainen vaihe epäonnistui: {title}")
                skipped.append((key, "optional"))
            else:
                failed.append((key, "failed"))

    print("\n========================================")
    if not failed:
        print(" FULL PIPELINE COMPLETED SUCCESSFULLY")
        if skipped:
            print(f" (valinnaiset ohitettiin: {', '.join(k for k, _ in skipped)})")
        print(" Reports in output/validation/")
    else:
        print(" PIPELINE COMPLETED WITH ERRORS")
        for key, reason in failed:
            print(f"   - {key}: {reason}")
        if skipped:
            print(f" Valinnaiset ohitettiin: {', '.join(k for k, _ in skipped)}")
    print("========================================")

    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
