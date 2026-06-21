from __future__ import annotations

from pathlib import Path

import pytest

from git_command_center.services.platform import directory_open_command


@pytest.mark.parametrize(
    ("platform", "executable"),
    [("win32", "explorer.exe"), ("darwin", "open"), ("linux", "xdg-open")],
)
def test_directory_open_command_uses_native_file_manager(
    tmp_path: Path,
    platform: str,
    executable: str,
) -> None:
    command = directory_open_command(tmp_path, platform=platform)

    assert command == [executable, str(tmp_path.resolve())]


def test_directory_open_command_rejects_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError):
        directory_open_command(tmp_path / "missing")
