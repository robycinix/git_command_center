from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class SandboxDeletionError(RuntimeError):
    """Raised when a directory is not a sandbox owned by GCC."""


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
        (root / ".git" / "gcc-sandbox").write_text("owned by GCC\n", encoding="utf-8")
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

    def delete(self, path: Path) -> None:
        sandbox = path.resolve()
        temporary_root = Path(tempfile.gettempdir()).resolve()
        marker = sandbox / ".git" / "gcc-sandbox"
        if (
            sandbox.parent != temporary_root
            or not sandbox.name.startswith("gcc-sandbox-")
            or not marker.is_file()
        ):
            raise SandboxDeletionError("Refusing to delete a directory not owned by GCC")
        for child in sandbox.rglob("*"):
            child.chmod(0o700 if child.is_dir() else 0o600)
        sandbox.chmod(0o700)
        shutil.rmtree(sandbox)
