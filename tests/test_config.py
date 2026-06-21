from __future__ import annotations

from pathlib import Path

from git_command_center.config.settings import AppSettings, load_settings, save_settings


def test_settings_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    expected = AppSettings(theme="nord", history_limit=42)
    save_settings(expected, path)
    assert load_settings(path) == expected
