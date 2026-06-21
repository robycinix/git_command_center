from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


class SimulationService:
    """Creates disposable repositories for risk-free exercises."""

    def create(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="gcc-sandbox-"))
        commands = [
            ["git", "init", "-b", "main"],
            ["git", "config", "user.name", "GCC Student"],
            ["git", "config", "user.email", "student@gcc.local"],
        ]
        for command in commands:
            subprocess.run(command, cwd=root, check=True, capture_output=True)
        readme = root / "README.md"
        readme.write_text(
            "# Safe Git sandbox\n\nEdit this file and experiment.\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "README.md"], cwd=root, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Start the GCC sandbox"],
            cwd=root,
            check=True,
            capture_output=True,
        )
        return root
