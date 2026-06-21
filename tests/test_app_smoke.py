from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from textual.widgets import Button, DataTable, Input, Select, Static

from git_command_center.config.settings import AppSettings
from git_command_center.git.service import GitService
from git_command_center.i18n import Translator
from git_command_center.ui.app import GCCApp


def test_app_mounts_and_loads_catalog(repository: Path) -> None:
    async def run() -> None:
        app = GCCApp(GitService(repository), AppSettings(refresh_interval=60))
        async with app.run_test(size=(160, 48)) as pilot:
            await pilot.pause()
            assert app.query_one("#repo-strip", Static)
            assert app.query_one("#command-table", DataTable).row_count > 0
            open_button = app.query_one("#open-sandbox", Button)
            assert open_button.disabled
            app._sandbox_ready(repository)
            assert not open_button.disabled

    asyncio.run(run())


@pytest.mark.parametrize("language", ["en", "de", "es", "fr", "pt", "it"])
def test_app_mounts_in_every_supported_language(repository: Path, language: str) -> None:
    async def run() -> None:
        settings = AppSettings.model_validate({"language": language, "refresh_interval": 60})
        translator = Translator(language)
        app = GCCApp(GitService(repository), settings, translator)
        async with app.run_test(size=(160, 48)) as pilot:
            await pilot.pause()
            search = app.query_one("#command-search", Input)
            language_select = app.query_one("#settings-language", Select)
            assert search.placeholder == translator("filter.search")
            assert language_select.value == language

    asyncio.run(run())
