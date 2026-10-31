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

import argparse
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from glfm.errors import ConfigError, DataError, GlfmError, OperationalError
from glfm.paths import get_data_dir

log = logging.getLogger(__name__)


# --- Step definitions -------------------------------------------------------
# Note: `download` is NOT part of the default pipeline.
#   - `download` is unnecessary because the pipeline builds the data itself.
#     Use separately: python3 -m glfm.download --tier consumer
#   - `pos_stats` requires ~3 GB of raw data. Use --with-pos, which will
#     download the Wiktextract dump automatically if it is missing.
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

# Step added only with --with-pos
POS_STEP = (
    "pos_stats",
    "Compute POS statistics (optional, requires ~3 GB raw data)",
    "glfm.tools.build_pos_stats",
    "optional",
)

# Module used to download the Wiktextract dump (only if --with-pos and
# the file is missing).
WIKTEXTTRACT_DOWNLOAD_MODULE = "glfm.tools.download_wiktextract"
WIKTEXTTRACT_FILENAME = "raw-wiktextract-data.jsonl.gz"

MODULE_ARGS = {
    "glfm.tools.build_consumer_dataset": ["-k", "20"],
}

TIMEOUTS = {
    "compute": None,      # no timeout (heavy)
    "build": 600,
    "generate": 300,
    "glottolog": 300,
    "consumer": 300,
    "pos_stats": None,    # POS computation may take a long time
    "wiktextract": 3600,  # download may take a long time
}
DEFAULT_TIMEOUT = 300


def setup_logging(log_dir: Path) -> Path:
    """Set up a Tee logger that writes to both stdout and a log file."""
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"pipeline_{stamp}.log"
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
    """Run a single pipeline step as a subprocess."""
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
        print(f"\n[TIMEOUT] {title} exceeded {timeout}s - killing.")
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


def build_epilog() -> str:
    """Build --help text dynamically from STEPS."""
    lines: list[str] = []

    lines.append("Available steps for --only / --skip:")
    for key, title, module, kind in STEPS:
        lines.append(f"  {key:12s} {title}")
    lines.append(f"  {POS_STEP[0]:12s} {POS_STEP[1]}")
    lines.append("")

    lines.append("Step types:")
    lines.append("  [required]   producer step - pipeline stops on failure")
    lines.append(
        "  [validator]  validator step - recorded on failure, "
        "pipeline continues"
    )
    lines.append(
        "  [optional]   optional step - skipped on failure, "
        "pipeline continues"
    )
    lines.append("")

    lines.append("Examples:")
    lines.append("  python3 -m glfm.run_full_pipeline")
    lines.append(
        "  python3 -m glfm.run_full_pipeline --with-pos"
    )
    lines.append(
        "  python3 -m glfm.run_full_pipeline --skip compute"
    )
    lines.append(
        "  python3 -m glfm.run_full_pipeline --only build compute consumer"
    )
    lines.append("  python3 -m glfm.run_full_pipeline --list")
    lines.append(
        "  python3 -m glfm.run_full_pipeline --list --with-pos"
    )
    lines.append("")

    lines.append("Notes:")
    lines.append("  - `download` is NOT part of the pipeline.")
    lines.append(
        "    Use `python3 -m glfm.download --tier consumer|research` "
        "separately."
    )
    lines.append(
        "  - `pos_stats` requires ~3 GB of raw Wiktextract data. "
        "With --with-pos, the data is downloaded automatically "
        "if missing."
    )
    lines.append(
        "  - Without POS data, `pos_stats` is an empty {} for each "
        "language."
    )

    return "\n".join(lines)


def ensure_wiktextract_data(data_root: Path) -> bool:
    """Download the Wiktextract dump if it is missing.

    Returns True if the data is available (already present or
    successfully downloaded), False otherwise.
    """
    path = data_root / WIKTEXTTRACT_FILENAME
    if path.exists():
        log.info(
            "Wiktextract data already present: %s (%.1f GB)",
            path, path.stat().st_size / 1e9,
        )
        return True

    print(
        f"\n[INFO] Wiktextract data missing ({path}). "
        f"Downloading (~3 GB)..."
    )
    ok = run_step(
        "Download Wiktextract dump",
        WIKTEXTTRACT_DOWNLOAD_MODULE,
        TIMEOUTS["wiktextract"],
    )
    if not ok:
        print(
            "\n[WARN] Could not download Wiktextract data. "
            "Skipping pos_stats."
        )
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="GLFM full pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=build_epilog(),
    )
    parser.add_argument(
        "--skip", nargs="*", default=[], metavar="KEY",
        help="Skip these steps (see available keys below)",
    )
    parser.add_argument(
        "--only", nargs="*", default=[], metavar="KEY",
        help="Run only these steps (see available keys below)",
    )
    parser.add_argument(
        "--with-pos",
        action="store_true",
        help=(
            "Include POS statistics (requires ~3 GB raw Wiktextract "
            "data). The data is downloaded automatically if missing."
        ),
    )
    parser.add_argument(
        "--list", action="store_true",
        help=(
            "List all available steps and exit (use --with-pos to "
            "include pos_stats)"
        ),
    )
    args = parser.parse_args()

    # Build the list of steps to run
    all_steps = list(STEPS)
    if args.with_pos:
        # Insert POS computation before validation
        insert_at = next(
            (i for i, s in enumerate(all_steps) if s[0] == "bcp47"),
            len(all_steps),
        )
        all_steps.insert(insert_at, POS_STEP)

    if args.list:
        for key, title, module, kind in all_steps:
            marker = {
                "producer": "[required]",
                "validator": "[validator]",
                "optional":  "[optional]",
            }[kind]
            print(f"  {key:12s} {title:55s} {marker}")
        return 0

    if args.only:
        steps = [s for s in all_steps if s[0] in args.only]
        if not steps:
            print(f"[ERROR] --only did not match any keys: {args.only}")
            print(
                f"        Available keys: "
                f"{', '.join(s[0] for s in all_steps)}"
            )
            return 1
    else:
        steps = [s for s in all_steps if s[0] not in args.skip]

    # Resolve data/log paths here, not at module import time.
    try:
        output_root = get_data_dir()
        log_dir = output_root / "logs"
    except (ConfigError, OSError) as e:
        print(f"[ERROR] Could not resolve data directory: {e}")
        return 1

    try:
        log_path = setup_logging(log_dir)
    except OSError as e:
        print(f"[ERROR] Could not set up logging: {e}")
        return 1

    print("========================================")
    print(" FULL PIPELINE EXECUTION")
    print("========================================")
    print(f"Log: {log_path}")
    print(f"Steps: {', '.join(s[0] for s in steps)}")
    if args.with_pos:
        print("POS statistics: enabled (--with-pos)")

    # If --with-pos is given and pos_stats is in the step list,
    # ensure the Wiktextract dump is present. Download it if missing.
    if args.with_pos and any(s[0] == "pos_stats" for s in steps):
        if not ensure_wiktextract_data(output_root):
            # Drop pos_stats from the step list, keep going.
            steps = [s for s in steps if s[0] != "pos_stats"]
            print("[INFO] pos_stats removed from this run.")

    failed = []
    skipped = []

    for key, title, module, kind in steps:
        timeout = TIMEOUTS.get(key, DEFAULT_TIMEOUT)
        extra_args = list(MODULE_ARGS.get(module, []))

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
            print(
                f" (optional steps skipped: "
                f"{', '.join(k for k, _ in skipped)})"
            )
        print(f" Reports in {output_root}/validation/")
    else:
        print(" PIPELINE COMPLETED WITH ERRORS")
        for key, reason in failed:
            print(f"   - {key}: {reason}")
    print("========================================")

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
