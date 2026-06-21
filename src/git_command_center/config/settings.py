from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError


class AISettings(BaseModel):
    enabled: bool = False
    provider: str = "none"
    model: str = ""


class AppSettings(BaseModel):
    language: Literal["auto", "en", "de", "es", "fr", "pt", "it"] = "auto"
    theme: str = "dark"
    refresh_interval: float = Field(default=3.0, ge=1.0, le=60.0)
    history_limit: int = Field(default=300, ge=20, le=10_000)
    confirm_destructive: bool = True
    shortcuts: dict[str, str] = Field(
        default_factory=lambda: {"refresh": "r", "quit": "q", "help": "f1"}
    )
    ai: AISettings = Field(default_factory=AISettings)


def config_directory() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "git-command-center"


def default_config_path() -> Path:
    return config_directory() / "config.yaml"


def save_settings(settings: AppSettings, path: Path | None = None) -> Path:
    target = path or default_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        yaml.safe_dump(settings.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )
    return target


def load_settings(path: Path | None = None) -> AppSettings:
    target = path or default_config_path()
    if not target.exists():
        settings = AppSettings()
        save_settings(settings, target)
        return settings
    try:
        raw: Any = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
        return AppSettings.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise ValueError(f"Invalid configuration at {target}: {error}") from error
