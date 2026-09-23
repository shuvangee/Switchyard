"""Exports response_text for the 13 coding + 5 revised debugging tasks
(009-013) from a local switchyard.db, for the two Groq models.

Why this exists: experiments/results/groq-gpt-oss-expansion.json never
captured response_text (a bug in run_groq_expansion.py's _to_record,
fixed going forward but not retroactively - see FAILURES_AND_LESSONS.md).
The raw text should still be sitting in the local SQLite database from
that run, though, since ModelExecutionORM always stores it - this reads
it back out without making any new API calls.

Run this on the SAME machine (and same backend/switchyard.db) the real
Groq run happened on:

    cd backend && source .venv/bin/activate
    python ../scripts/export_groq_code_responses.py

Then commit and push the resulting experiments/results/groq-code-
responses.json, same as the original results file.
"""

import json
import sqlite3
import sys
from pathlib import Path

TASK_IDS = [f"coding-{i:03d}" for i in range(1, 14)] + [f"debugging-{i:03d}" for i in range(9, 14)]
MODEL_IDS = ["groq-gpt-oss-20b", "groq-gpt-oss-120b"]


def main() -> None:
    db_path = Path(__file__).resolve().parents[1] / "backend" / "switchyard.db"
    if not db_path.exists():
        raise SystemExit(
            f"{db_path} not found - run this from the same machine/checkout the "
            "Groq run happened on, before deleting or resetting the local database."
        )

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    placeholders_task = ",".join("?" * len(TASK_IDS))
    placeholders_model = ",".join("?" * len(MODEL_IDS))
    rows = conn.execute(
        f"""
        SELECT task_id, model_config_id, status, response_text, error_message
        FROM model_executions
        WHERE task_id IN ({placeholders_task})
          AND model_config_id IN ({placeholders_model})
        ORDER BY task_id, model_config_id, id
        """,
        [*TASK_IDS, *MODEL_IDS],
    ).fetchall()
    conn.close()

    if not rows:
        raise SystemExit(
            "no matching rows found in model_executions - either the Groq run "
            "used a different database, or this table has since been cleared."
        )

    # Keep only the most recent execution per (task_id, model_config_id) in
    # case a task was ever run more than once (e.g. a retry pass).
    latest: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row["task_id"], row["model_config_id"])
        latest[key] = dict(row)

    records = list(latest.values())
    missing = [
        (tid, mid)
        for tid in TASK_IDS
        for mid in MODEL_IDS
        if (tid, mid) not in latest
    ]

    output = {
        "note": "response_text export from local switchyard.db - no new API calls",
        "task_count": len(TASK_IDS),
        "model_ids": MODEL_IDS,
        "executions": records,
    }
    results_path = Path(__file__).resolve().parents[1] / "experiments" / "results" / "groq-code-responses.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps(output, indent=2) + "\n")

    print(f"wrote {results_path.relative_to(Path(__file__).resolve().parents[1])}")
    print(f"found: {len(records)}/{len(TASK_IDS) * len(MODEL_IDS)} (task, model) rows")
    if missing:
        print(f"missing ({len(missing)}):")
        for tid, mid in missing:
            print(f"  {tid} / {mid}")


if __name__ == "__main__":
    main()
