"""Regression proof for direct-path project-learning CLI startup."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINTS = (
    Path("scripts/run_project_driven_learning.py"),
    Path("scripts/resume_project_learning_worker.py"),
)


def test_direct_terminal_entrypoints_bootstrap_repository_imports() -> None:
    """The documented ``python scripts/...`` form must reach argparse cleanly."""

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONNOUSERSITE"] = "1"

    for relative in ENTRYPOINTS:
        completed = subprocess.run(
            [sys.executable, str(ROOT / relative), "--help"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert completed.returncode == 0, (
            f"{relative} failed direct-path startup\nstdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
        assert "usage:" in completed.stdout.lower()
