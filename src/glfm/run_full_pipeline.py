#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Global Language Family Mapper (GLFM)
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.0.5
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT = PROJECT_ROOT / "output"
LOG_DIR = OUTPUT / "logs"


# --- Step definitions -------------------------------------------------------
STEPS = [
    ("download",  "Download data (consumer)",
     "glfm.download", "producer"),
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

# Module-specific arguments
MODULE_ARGS = {
    "glfm.download": ["--tier", "consumer"],
    "glfm.tools.build_consumer_dataset": ["-k", "20"],
}

# Timeouts in seconds. None = no timeout
TIMEOUTS = {
    "download": 300,
    "compute": None,
    "build": 600,
    "generate": 300,
    "glottolog": 300,
    "consumer": 300,
}
DEFAULT_TIMEOUT = 300


def setup_logging():
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

    sys.stdout = Tee(sys.stdout, log_file)
    sys.stderr = Tee(sys.stderr, log_file)
    return log_path


def run_step(
    title: str,
    module: str,
    timeout: int | None,
    extra_args: list[str] | None = None,
) -> bool:
    print(f"\n=== {title} ===")
    print(f"Module: {module}")
    if extra_args:
        print(f"Args: {' '.join(extra_args)}")
    if timeout:
        print(f"Timeout: {timeout}s")

    cmd = [sys.executable, "-m", module] + (extra_args or [])

    try:
        process = subprocess.Popen(cmd)
    except OSError as e:
        print(f"[ERROR] {e}")
        return False

    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"\n[TIMEOUT] {title} exceeded {timeout}s – killing.")
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
Examples:
  python3 -m glfm.run_full_pipeline                      # all steps
  python3 -m glfm.run_full_pipeline --tier research      # research data
  python3 -m glfm.run_full_pipeline --skip download      # skip data download
  python3 -m glfm.run_full_pipeline --skip compute       # skip heavy computation
  python3 -m glfm.run_full_pipeline --only build bcp47   # run only selected steps
  python3 -m glfm.run_full_pipeline --list               # list steps
""",
    )
    parser.add_argument(
        "--tier",
        choices=["consumer", "research"],
        default="consumer",
        help="Data package: consumer (558 kB) or research (1.4 MB)",
    )
    parser.add_argument(
        "--skip", nargs="*", default=[], metavar="KEY",
        help="Skip these steps",
    )
    parser.add_argument(
        "--only", nargs="*", default=[], metavar="KEY",
        help="Run only these steps",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List steps and exit",
    )
    args = parser.parse_args()

    if args.list:
        for key, title, module, kind in STEPS:
            marker = {
                "producer": "[required]",
                "validator": "[validator]",
                "optional":  "[optional]",
            }[kind]
            print(f"  {key:10s} {title:35s} {marker}")
        return

    if args.only:
        steps = [s for s in STEPS if s[0] in args.only]
        if not steps:
            print(f"[ERROR] --only did not match any keys: {args.only}")
            sys.exit(1)
    else:
        steps = [s for s in STEPS if s[0] not in args.skip]

    log_path = setup_logging()
    print("========================================")
    print(" FULL PIPELINE EXECUTION")
    print("========================================")
    print(f"Log: {log_path}")
    print(f"Tier: {args.tier}")
    print(f"Steps: {', '.join(s[0] for s in steps)}")

    failed = []
    skipped = []

    for key, title, module, kind in steps:
        timeout = TIMEOUTS.get(key, DEFAULT_TIMEOUT)

        # Tier-specific arguments for the download step
        extra_args = list(MODULE_ARGS.get(module, []))
        if module == "glfm.download" and args.tier != "consumer":
            extra_args = ["--tier", args.tier]

        ok = run_step(title, module, timeout, extra_args)

        if not ok:
            if kind == "producer":
                print(f"\n[STOP] Producer step failed: {title}")
                failed.append((key, "failed"))
                break
            elif kind == "optional":
                print(f"\n[SKIP] Optional step failed: {title}")
                skipped.append((key, "optional"))
            else:
                failed.append((key, "failed"))

    print("\n========================================")
    if not failed:
        print(" FULL PIPELINE COMPLETED SUCCESSFULLY")
        if skipped:
            print(f" (optional steps skipped: {', '.join(k for k, _ in skipped)})")
        print(" Reports in output/validation/")
    else:
        print(" PIPELINE COMPLETED WITH ERRORS")
        for key, reason in failed:
            print(f"   - {key}: {reason}")
    print("========================================")

    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
