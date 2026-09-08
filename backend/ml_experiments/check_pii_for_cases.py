#!/usr/bin/env python3
"""
Scans every case in CASES_FILE for PII, using the same check_pii() the real
generate_email() route uses. No DB, no OpenAI calls, no CSV - just prints
which case ids would get rejected, so you can fix them before a full run.

Usage (from inside backend/):
    uv run python experiments/check_pii_for_cases.py
"""
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.api.routes.email import check_pii  # noqa: E402

CASES_FILE = BACKEND_DIR / "experiments" / "inputs" / "case_set_1.json"


def main() -> None:
    cases = json.loads(CASES_FILE.read_text())

    flagged = []
    for case in cases:
        safe_text, pii_found = check_pii(case["case_details"])
        if pii_found:
            flagged.append(case["id"])
            # safe_text has each detected span replaced inline with a tag like
            # <PERSON>, <IN_PAN>, <EMAIL_ADDRESS> - shows both what and where.
            print(f"PII DETECTED: {case['id']}")
            print(f"  redacted preview: {safe_text}\n")

    if not flagged:
        print(f"No PII detected in any of the {len(cases)} cases.")
    else:
        print(f"\n{len(flagged)}/{len(cases)} case(s) flagged: {flagged}")


if __name__ == "__main__":
    main()
