"""Offline controlled demonstration of loop statistics on sample corpus topics."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_scripted_three_topic_demo_reduces_seeded_unsupported_claims() -> None:
    project_root = Path(__file__).resolve().parents[1]
    script = project_root / "scripts" / "offline_revision_demo.py"
    completed = subprocess.run(
        [sys.executable, str(script), "--json"],
        cwd=project_root,
        capture_output=True,
        check=True,
        text=True,
        timeout=30,
    )
    rows = json.loads(completed.stdout)

    assert len(rows) == 3
    assert all(row["initial_unsupported"] == 1 for row in rows)
    assert all(row["final_unsupported"] == 0 for row in rows)
    assert all(row["revisions"] == 1 and row["stop_reason"] == "clean" for row in rows)
