#!/usr/bin/env python3
"""
Runs generate_email() for every case in CASES_FILE, REPEATS times each, and
appends the results to OUTPUT_CSV. Retries a failed call once.

CASES_FILE is a JSON list of {"id": ..., "case_details": ...} objects.

Usage (from inside backend/):
    uv run python experiments/run_email_experiment.py
"""
import csv
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlmodel import Session  # noqa: E402

from app import crud  # noqa: E402
from app.api.routes.email import generate_email  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.db import engine  # noqa: E402
from app.models.email import EmailGenerateRequest  # noqa: E402

# --- Edit these for each run ---
EXPERIMENT_NUMBER = 1  # bump this every time you start a new experiment
EXPERIMENT_DESCRIPTION = "baseline"  # e.g. "baseline" or "tried reordering the policy section"
CASES_FILE = BACKEND_DIR / "experiments" / "inputs" / "case_set_1.json"
OUTPUT_CSV = BACKEND_DIR / "experiments" / "results" / "results_experiment_1.csv"
#--------------------------------

#--- OTHER Configs 
REPEATS = 10  # how many times to run each case
REQUEST_DELAY_SECONDS = 2  

# --------------------------------

CSV_HEADER = [
    "experiment_number",
    "experiment_description",
    "commit_id",
    "prompt_id",
    "case_details_created_by",
    "run_number",
    "timestamp",
    "user_query",
    "output",
    "conversation_id",
    "message_id",
    "error",
    "retried",
]


def call_with_retry(session: Session, user, case_details: str) -> dict:
    """Calls generate_email, retrying once if it fails. Never raises."""
    for attempt in (1, 2):
        try:
            response = generate_email(
                body=EmailGenerateRequest(case_details=case_details),
                session=session,
                current_user=user,
            )
            if attempt == 2:
                print("  retry succeeded")
            return {
                "output": response.email,
                "conversation_id": str(response.conversation_id),
                "message_id": str(response.message_id),
                "error": "",
                "retried": attempt == 2,
            }
        except Exception as e:
            if attempt == 1:
                print(f"  attempt 1 failed ({e}), retrying once...")
                continue
            print(f"  retry also failed ({e}), giving up on this case")
            return {
                "output": "",
                "conversation_id": "",
                "message_id": "",
                "error": str(getattr(e, "detail", e)),
                "retried": True,
            }


def get_commit_id() -> str:
    """Reads the currently checked-out commit - never writes to git.
    Refuses to run on a dirty tree so the recorded id is never a lie."""
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    if status.strip():
        sys.exit(
            "You have uncommitted changes. Commit first so this run's commit_id "
            "actually matches the code that produced it, then re-run this script."
        )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def main() -> None:
    """Runs every case in CASES_FILE REPEATS times and appends each result to OUTPUT_CSV."""
    commit_id = get_commit_id()
    cases = json.loads(CASES_FILE.read_text())

    with Session(engine) as session:
        user = crud.get_user_by_email(session=session, email=settings.FIRST_SUPERUSER)
        if user is None:
            sys.exit(f"seeded user {settings.FIRST_SUPERUSER!r} not found in the DB")

        is_new_file = not OUTPUT_CSV.exists()
        with open(OUTPUT_CSV, "a", newline="") as f:
            writer = csv.writer(f)
            if is_new_file:
                writer.writerow(CSV_HEADER)

            for case in cases:
                prompt_id = case["id"]
                case_details = case["case_details"]
                created_by = case.get("created_by", "")  # optional field
                for run_number in range(1, REPEATS + 1):
                    print(f"Running case {prompt_id!r}, run {run_number}/{REPEATS}...")
                    result = call_with_retry(session, user, case_details)
                    writer.writerow(
                        [
                            EXPERIMENT_NUMBER,
                            EXPERIMENT_DESCRIPTION,
                            commit_id,
                            prompt_id,
                            created_by,
                            run_number,
                            datetime.now(timezone.utc).isoformat(),
                            case_details,
                            result["output"],
                            result["conversation_id"],
                            result["message_id"],
                            result["error"],
                            result["retried"],
                        ]
                    )
                    f.flush()
                    time.sleep(REQUEST_DELAY_SECONDS)

    print(f"Done. Results appended to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
