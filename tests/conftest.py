from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def run_git(path: Path, *arguments: str) -> str:
    process = subprocess.run(
        ["git", *arguments],
        cwd=path,
        capture_output=True,
        text=True,
        check=True,
    )
    return process.stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    run_git(tmp_path, "init", "-b", "main")
    run_git(tmp_path, "config", "user.name", "GCC Tester")
    run_git(tmp_path, "config", "user.email", "test@gcc.local")
    (tmp_path / "tracked.txt").write_text("first\n", encoding="utf-8")
    run_git(tmp_path, "add", "tracked.txt")
    run_git(tmp_path, "commit", "-m", "Initial commit")
    return tmp_path
