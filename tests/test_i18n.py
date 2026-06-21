from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pytest
import yaml

from git_command_center.config.settings import AppSettings, load_settings, save_settings
from git_command_center.i18n import SUPPORTED_LANGUAGES, Translator, resolve_language
from git_command_center.services.catalog import CommandCatalog
from git_command_center.services.planner import build_plan


@pytest.mark.parametrize(
    ("system_locale", "expected"),
    [
        ("de_DE.UTF-8", "de"),
        ("es-ES", "es"),
        ("fr_FR", "fr"),
        ("pt_BR", "pt"),
        ("it_IT", "it"),
        ("ja_JP", "en"),
    ],
)
def test_automatic_language_detection(system_locale: str, expected: str) -> None:
    assert resolve_language("auto", system_locale=system_locale) == expected


def test_every_supported_language_loads_and_falls_back_to_english() -> None:
    for language in SUPPORTED_LANGUAGES:
        translator = Translator(language)
        assert translator("app.subtitle") != "app.subtitle"
        assert translator("category.repository") != "category.repository"


def test_translation_catalogs_have_identical_keys() -> None:
    resources = files("git_command_center.data.locales")
    catalogs = {
        language: yaml.safe_load(
            resources.joinpath(f"{language}.yaml").read_text(encoding="utf-8")
        )
        for language in SUPPORTED_LANGUAGES
    }
    english_keys = set(catalogs["en"])

    assert english_keys
    assert all(set(catalog) == english_keys for catalog in catalogs.values())


def test_translated_plans_keep_git_arguments_stable() -> None:
    english = build_plan("branch", value="feature/i18n", translator=Translator("en"))
    italian = build_plan("branch", value="feature/i18n", translator=Translator("it"))

    assert english.title != italian.title
    assert english.commands == italian.commands == [["switch", "-c", "feature/i18n"]]


def test_language_preference_is_persisted(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    save_settings(AppSettings(language="fr"), path)

    assert load_settings(path).language == "fr"


def test_automatic_language_is_the_initial_preference() -> None:
    assert AppSettings().language == "auto"


def test_command_catalog_uses_localized_data_with_fallback() -> None:
    english = CommandCatalog(language="en").get("init")
    italian = CommandCatalog(language="it").get("init")
    german = CommandCatalog(language="de").get("init")

    assert english.description != italian.description
    assert german.description == english.description
