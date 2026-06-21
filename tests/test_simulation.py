from __future__ import annotations

from pathlib import Path

import pytest

from git_command_center.services.simulation import (
    SandboxDeletionError,
    SimulationService,
)


def test_created_sandbox_can_be_deleted() -> None:
    service = SimulationService()
    sandbox = service.create()

    assert sandbox.is_dir()
    assert (sandbox / ".git" / "gcc-sandbox").is_file()

    service.delete(sandbox)

    assert not sandbox.exists()


def test_delete_rejects_directory_not_owned_by_gcc(tmp_path: Path) -> None:
    service = SimulationService()

    with pytest.raises(SandboxDeletionError):
        service.delete(tmp_path)

    assert tmp_path.is_dir()
