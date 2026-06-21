from __future__ import annotations

import locale
import os
from importlib.resources import files
from typing import Any, Final, Literal

import yaml
from pydantic import TypeAdapter

Language = Literal["en", "de", "es", "fr", "pt", "it"]
LanguageSetting = Literal["auto", "en", "de", "es", "fr", "pt", "it"]

SUPPORTED_LANGUAGES: Final[tuple[Language, ...]] = ("en", "de", "es", "fr", "pt", "it")
DEFAULT_LANGUAGE: Final[Language] = "en"


def _system_locale() -> str:
    for variable in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(variable)
        if value:
            return value
    detected, _encoding = locale.getlocale()
    return detected or ""


def resolve_language(requested: str = "auto", *, system_locale: str | None = None) -> Language:
    normalized = requested.strip().lower().replace("_", "-")
    if normalized != "auto":
        prefix = normalized.split("-", 1)[0]
        return prefix if prefix in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE

    detected = (system_locale if system_locale is not None else _system_locale()).lower()
    detected = detected.replace("_", "-").split(".", 1)[0]
    prefix = detected.split("-", 1)[0]
    return prefix if prefix in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def _load_catalog(language: Language) -> dict[str, str]:
    resource = files("git_command_center.data.locales").joinpath(f"{language}.yaml")
    raw: Any = yaml.safe_load(resource.read_text(encoding="utf-8")) or {}
    return TypeAdapter(dict[str, str]).validate_python(raw)


class Translator:
    """Resolve message keys with an English fallback catalog."""

    def __init__(self, language: str = "auto", *, system_locale: str | None = None) -> None:
        self.language = resolve_language(language, system_locale=system_locale)
        self._fallback = _load_catalog(DEFAULT_LANGUAGE)
        self._catalog = (
            self._fallback if self.language == DEFAULT_LANGUAGE else _load_catalog(self.language)
        )

    def t(self, key: str, **values: object) -> str:
        template = self._catalog.get(key, self._fallback.get(key, key))
        if not values:
            return template
        try:
            return template.format_map(values)
        except (KeyError, ValueError) as error:
            raise ValueError(f"Invalid translation parameters for {key!r}: {error}") from error

    def __call__(self, key: str, **values: object) -> str:
        return self.t(key, **values)
