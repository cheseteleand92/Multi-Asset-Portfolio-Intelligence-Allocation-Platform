from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_script(relative_path: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONWARNINGS"] = "error"
    return subprocess.run(
        [sys.executable, relative_path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env=env,
    )


def test_run_demo_script_executes_cleanly():
    result = _run_script("tests/run_demo.py")

    assert result.returncode == 0, result.stderr
    assert "[SUCCESS] Pipeline verified." in result.stdout
    assert result.stderr == ""


def test_backtest_example_executes_cleanly():
    result = _run_script("examples/backtest_example.py")

    assert result.returncode == 0, result.stderr
    assert "Final NAV:" in result.stdout
    assert "Annualized Return:" in result.stdout
    assert result.stderr == ""
