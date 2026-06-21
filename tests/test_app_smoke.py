from __future__ import annotations

import asyncio
from pathlib import Path

from textual.widgets import DataTable, Static

from git_command_center.config.settings import AppSettings
from git_command_center.git.service import GitService
from git_command_center.ui.app import GCCApp


def test_app_mounts_and_loads_catalog(repository: Path) -> None:
    async def run() -> None:
        app = GCCApp(GitService(repository), AppSettings(refresh_interval=60))
        async with app.run_test(size=(160, 48)) as pilot:
            await pilot.pause()
            assert app.query_one("#repo-strip", Static)
            assert app.query_one("#command-table", DataTable).row_count > 0

    asyncio.run(run())
