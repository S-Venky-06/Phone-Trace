#!/usr/bin/env python3
"""
PhoneTrace — Synthetic Evidence Generator (Phase 1 Entry Point)
================================================================

Generates synthetic Android forensic evidence for a complete case scenario.

Usage:
    python evidence_generator/main_generate.py

Output:
    evidence_output/
        calllog.db          — Call log database
        mmssms.db           — SMS database
        chrome_history.db   — Chrome browser history
        gps_log.json        — GPS location pings
        app_usage.db        — App foreground/background events
        file_metadata.json  — File system metadata

All output is deterministic (random.seed(42)) and internally consistent.
"""

import io
import random
import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace"
    )

# Ensure the project root is on sys.path so that `case_config` is importable
# regardless of the working directory.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import case_config as cfg
from evidence_generator.utils import get_output_dir, setup_logging
from evidence_generator.generate_calls import generate_call_log
from evidence_generator.generate_sms import generate_sms_log
from evidence_generator.generate_browser import generate_browser_history
from evidence_generator.generate_gps import generate_gps_log
from evidence_generator.generate_app_usage import generate_app_usage
from evidence_generator.generate_file_metadata import generate_file_metadata


def _print_banner() -> None:
    """Print the application banner."""
    print("=" * 65)
    print("  PhoneTrace -- Synthetic Forensic Evidence Generator (Phase 1)")
    print("=" * 65)
    print()


def _print_summary(results: dict, elapsed: float) -> None:
    """Print a developer summary of the generation run.

    Args:
        results: Dict mapping generator names to their statistics.
        elapsed: Total wall-clock time in seconds.
    """
    output_dir = get_output_dir()

    print()
    print("=" * 65)
    print("  GENERATION SUMMARY")
    print("=" * 65)
    print()

    # Record counts
    print("  Records Generated:")
    print(f"    Call log .......... {results['calls']['total_records']:>6} records")
    print(f"    SMS ............... {results['sms']['total_records']:>6} records")
    print(f"    Browser history ... {results['browser']['total_records']:>6} records")
    print(f"    GPS pings ......... {results['gps']['total_records']:>6} records")
    print(f"    App usage ......... {results['app_usage']['total_records']:>6} records"
          f"  ({results['app_usage']['total_sessions']} sessions)")
    print(f"    File metadata ..... {results['file_metadata']['total_records']:>6} records")
    print()

    total = sum(r["total_records"] for r in results.values())
    print(f"    TOTAL ............. {total:>6} records")
    print()

    # Output directory
    print(f"  Output Directory: {output_dir}")
    print()

    # Case details
    print("  Case Configuration:")
    print(f"    Suspect ........... {cfg.SUSPECT_NAME}")
    print(f"    Baseline .......... {cfg.BASELINE_START.strftime('%Y-%m-%d')} to "
          f"{cfg.BASELINE_END.strftime('%Y-%m-%d')} ({cfg.BASELINE_DAYS} days)")
    print(f"    Incident Window ... {cfg.INCIDENT_START.strftime('%Y-%m-%d %H:%M')} to "
          f"{cfg.INCIDENT_END.strftime('%H:%M')} IST")
    print(f"    Alibi Location .... {cfg.ALIBI_LOCATION['name']}")
    print(f"    Actual Location ... {cfg.INCIDENT_LOCATION['name']}")
    print()

    # Injected anomalies
    print("  Injected Anomalies:")
    print(f"    [+] Suspicious calls to burner number ... {results['calls']['suspicious_calls']}")
    print(f"    [+] Missing call log entry .............. {results['calls']['missing_call_injected']}")
    print(f"    [+] Suspicious SMS messages ............. {results['sms']['suspicious_sms']}")
    print(f"    [+] GPS at wrong location ............... {results['gps']['gps_anomaly_pings']} pings")
    print(f"    [+] Timezone inconsistency (Chrome) ..... {results['browser']['timezone_anomaly_injected']}")
    print(f"    [+] Duplicate contact spelling .......... Vikram Singh / Vikrm Singh")
    print()

    # Completion status
    print(f"  Status: COMPLETE ({elapsed:.2f}s)")
    print()
    print("=" * 65)


def main() -> None:
    """Run all evidence generators and print the summary."""
    _print_banner()

    # Deterministic generation
    random.seed(cfg.RANDOM_SEED)

    logger = setup_logging()
    logger.info("Starting evidence generation (seed=%d)", cfg.RANDOM_SEED)

    # Ensure output directory exists
    output_dir = get_output_dir()
    logger.info("Output directory: %s", output_dir)

    # Clean old evidence files to prevent record accumulation
    for f in output_dir.glob("*"):
        if f.is_file() and f.suffix in (".db", ".json"):
            try:
                f.unlink()
                logger.info("Cleaned stale evidence: %s", f.name)
            except OSError as exc:
                logger.warning("Could not delete %s: %s", f.name, exc)

    start_time = time.time()

    # Run all generators
    results = {}

    print("  [1/6] Generating call log ............", end=" ", flush=True)
    results["calls"] = generate_call_log()
    print("OK")

    print("  [2/6] Generating SMS log .............", end=" ", flush=True)
    results["sms"] = generate_sms_log()
    print("OK")

    print("  [3/6] Generating browser history .....", end=" ", flush=True)
    results["browser"] = generate_browser_history()
    print("OK")

    print("  [4/6] Generating GPS log .............", end=" ", flush=True)
    results["gps"] = generate_gps_log()
    print("OK")

    print("  [5/6] Generating app usage ...........", end=" ", flush=True)
    results["app_usage"] = generate_app_usage()
    print("OK")

    print("  [6/6] Generating file metadata .......", end=" ", flush=True)
    results["file_metadata"] = generate_file_metadata()
    print("OK")

    elapsed = time.time() - start_time

    _print_summary(results, elapsed)
    logger.info("Evidence generation complete.")


if __name__ == "__main__":
    main()
