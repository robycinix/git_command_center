from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def directory_open_command(directory: Path, *, platform: str = sys.platform) -> list[str]:
    target = directory.resolve()
    if not target.is_dir():
        raise NotADirectoryError(target)
    if platform == "win32":
        return ["explorer.exe", str(target)]
    if platform == "darwin":
        return ["open", str(target)]
    return ["xdg-open", str(target)]


def open_directory(directory: Path) -> None:
    subprocess.Popen(
        directory_open_command(directory),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
