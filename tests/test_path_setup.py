from __future__ import annotations

from pathlib import Path

from git_command_center.services.path_setup import (
    PathSetupStatus,
    path_contains,
    setup_user_path,
)


def test_path_membership_can_be_case_insensitive() -> None:
    target = Path("C:/Users/Example/Python/Scripts")
    value = "C:/Windows;C:/USERS/EXAMPLE/PYTHON/SCRIPTS"

    assert path_contains(value, target, separator=";", case_sensitive=False)


def test_windows_path_is_added_once(tmp_path: Path) -> None:
    scripts = (tmp_path / "Python" / "Scripts").resolve()
    writes: list[str] = []

    added = setup_user_path(
        scripts,
        platform="nt",
        environment={"PATH": "C:\\Windows"},
        windows_reader=lambda: "C:\\Tools",
        windows_writer=writes.append,
    )

    assert added.status is PathSetupStatus.ADDED
    assert writes == [f"C:\\Tools;{scripts}"]

    already_present = setup_user_path(
        scripts,
        platform="nt",
        environment={"PATH": "C:\\Windows"},
        windows_reader=lambda: writes[0],
        windows_writer=writes.append,
    )

    assert already_present.status is PathSetupStatus.ALREADY_PRESENT
    assert len(writes) == 1


def test_posix_profile_is_created_idempotently(tmp_path: Path) -> None:
    scripts = (tmp_path / ".local" / "bin").resolve()
    home = tmp_path / "home"
    environment = {"PATH": "/usr/local/bin:/usr/bin", "SHELL": "/bin/bash"}

    added = setup_user_path(
        scripts,
        platform="posix",
        home=home,
        environment=environment,
    )
    profile = home / ".profile"

    assert added.status is PathSetupStatus.ADDED
    assert str(scripts) in profile.read_text(encoding="utf-8")

    already_present = setup_user_path(
        scripts,
        platform="posix",
        home=home,
        environment=environment,
    )

    assert already_present.status is PathSetupStatus.ALREADY_PRESENT
    assert profile.read_text(encoding="utf-8").count("Added by Git Command Center") == 1
