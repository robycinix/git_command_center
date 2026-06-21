from __future__ import annotations

import ctypes
import os
import shlex
import shutil
import site
import sys
import sysconfig
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class PathSetupStatus(StrEnum):
    ADDED = "added"
    ALREADY_PRESENT = "already_present"


@dataclass(frozen=True)
class PathSetupResult:
    status: PathSetupStatus
    scripts_directory: Path
    profile: Path | None = None


class PathSetupError(RuntimeError):
    """Raised when the installed console launcher cannot be located."""


def _normalized(value: str, *, case_sensitive: bool) -> str:
    normalized = os.path.normpath(os.path.expandvars(value.strip().strip('"')))
    return normalized if case_sensitive else normalized.casefold()


def path_contains(
    path_value: str,
    directory: Path,
    *,
    separator: str = os.pathsep,
    case_sensitive: bool = os.name != "nt",
) -> bool:
    expected = _normalized(str(directory), case_sensitive=case_sensitive)
    return any(
        _normalized(entry, case_sensitive=case_sensitive) == expected
        for entry in path_value.split(separator)
        if entry.strip()
    )


def _candidate_script_directories() -> list[Path]:
    candidates: list[Path] = []
    located = shutil.which("gcc-tui")
    if located:
        candidates.append(Path(located).resolve().parent)

    user_scheme = "nt_user" if os.name == "nt" else "posix_user"
    for scheme in (user_scheme, sysconfig.get_default_scheme()):
        try:
            scripts = sysconfig.get_path("scripts", scheme=scheme)
        except KeyError:
            continue
        if scripts:
            candidates.append(Path(scripts).expanduser())

    candidates.extend([Path(sys.executable).resolve().parent, Path.home() / ".local" / "bin"])
    user_base = site.USER_BASE
    if user_base:
        candidates.append(Path(user_base).expanduser() / "bin")
    if os.name == "nt" and user_base:
        version = f"Python{sys.version_info.major}{sys.version_info.minor}"
        candidates.append(Path(user_base).expanduser() / version / "Scripts")

    unique: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in unique:
            unique.append(resolved)
    return unique


def find_scripts_directory() -> Path:
    launcher_names = ("gcc-tui.exe", "gcc-tui") if os.name == "nt" else ("gcc-tui",)
    for directory in _candidate_script_directories():
        if any((directory / name).is_file() for name in launcher_names):
            return directory
    raise PathSetupError("gcc-tui launcher not found")


def _read_windows_user_path() -> str:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _kind = winreg.QueryValueEx(key, "Path")
            return str(value)
    except FileNotFoundError:
        return ""


def _write_windows_user_path(value: str) -> None:
    import winreg

    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, "Environment") as key:
        kind = winreg.REG_EXPAND_SZ if "%" in value else winreg.REG_SZ
        winreg.SetValueEx(key, "Path", 0, kind, value)

    try:
        result = ctypes.c_size_t()
        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF,
            0x001A,
            0,
            "Environment",
            0x0002,
            5_000,
            ctypes.byref(result),
        )
    except (AttributeError, OSError):
        pass


def _profile_path(home: Path, environment: Mapping[str, str]) -> Path:
    shell = environment.get("SHELL", "")
    if shell.endswith("zsh"):
        return home / ".zprofile"
    return home / ".profile"


def setup_user_path(
    scripts_directory: Path | None = None,
    *,
    platform: str = os.name,
    home: Path | None = None,
    environment: Mapping[str, str] | None = None,
    windows_reader: Callable[[], str] = _read_windows_user_path,
    windows_writer: Callable[[str], None] = _write_windows_user_path,
) -> PathSetupResult:
    target = (scripts_directory or find_scripts_directory()).resolve()
    current_environment = environment or os.environ

    if platform == "nt":
        user_path = windows_reader()
        effective_path = ";".join(filter(None, [user_path, current_environment.get("PATH", "")]))
        if path_contains(effective_path, target, separator=";", case_sensitive=False):
            return PathSetupResult(PathSetupStatus.ALREADY_PRESENT, target)
        updated = f"{user_path.rstrip(';')};{target}" if user_path else str(target)
        windows_writer(updated)
        return PathSetupResult(PathSetupStatus.ADDED, target)

    profile = _profile_path(home or Path.home(), current_environment)
    existing_profile = profile.read_text(encoding="utf-8") if profile.exists() else ""
    if (
        path_contains(current_environment.get("PATH", ""), target)
        or str(target) in existing_profile
    ):
        return PathSetupResult(PathSetupStatus.ALREADY_PRESENT, target, profile)

    profile.parent.mkdir(parents=True, exist_ok=True)
    prefix = "" if not existing_profile or existing_profile.endswith("\n") else "\n"
    export_line = f"export PATH={shlex.quote(str(target))}:\"$PATH\""
    with profile.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(f"{prefix}\n# Added by Git Command Center\n{export_line}\n")
    return PathSetupResult(PathSetupStatus.ADDED, target, profile)
