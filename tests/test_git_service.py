from __future__ import annotations

from pathlib import Path

from git_command_center.core.models import CommandPlan, RiskLevel
from git_command_center.git.service import GitService


def test_snapshot_reports_worktree_states(repository: Path) -> None:
    (repository / "tracked.txt").write_text("changed\n", encoding="utf-8")
    (repository / "staged.txt").write_text("staged\n", encoding="utf-8")
    (repository / "new.txt").write_text("new\n", encoding="utf-8")
    service = GitService(repository)
    service.execute(
        CommandPlan(
            title="Stage",
            explanation="Stage one file",
            commands=[["add", "staged.txt"]],
            risk=RiskLevel.LOW,
        )
    )

    snapshot = service.snapshot()

    assert snapshot.branch == "main"
    assert snapshot.modified_count == 2
    assert snapshot.staged_count == 1
    assert snapshot.untracked_count == 1
    assert snapshot.last_commit_message == "Initial commit"


def test_history_branch_diff_and_reflog(repository: Path) -> None:
    service = GitService(repository)
    (repository / "tracked.txt").write_text("first\nsecond\n", encoding="utf-8")

    assert service.commits()[0].message == "Initial commit"
    assert any(branch.active and branch.name == "main" for branch in service.branches())
    assert "+second" in service.diff()
    assert service.reflog()[0].action == "commit (initial)"


def test_execute_stops_after_failure(repository: Path) -> None:
    service = GitService(repository)
    results = service.execute(
        CommandPlan(
            title="Fail",
            explanation="First command fails",
            commands=[["switch", "missing"], ["status"]],
            risk=RiskLevel.LOW,
        )
    )
    assert len(results) == 1
    assert not results[0].succeeded
