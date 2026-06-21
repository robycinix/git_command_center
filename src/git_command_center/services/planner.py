from __future__ import annotations

from git_command_center.core.models import CommandPlan, RiskLevel
from git_command_center.i18n import Translator

GOALS: tuple[str, ...] = (
    "save",
    "push",
    "pull",
    "branch",
    "undo_commit",
    "recover_file",
    "conflicts",
)


def build_plan(
    goal: str,
    *,
    value: str = "",
    translator: Translator | None = None,
) -> CommandPlan:
    tr = translator or Translator("en")
    value = value.strip()
    if goal == "save":
        message = value or tr("planner.default_commit_message")
        return CommandPlan(
            title=tr("planner.save.title"),
            explanation=tr("planner.save.explanation"),
            commands=[["add", "--all"], ["commit", "-m", message]],
            risk=RiskLevel.LOW,
            rollback=tr("planner.save.rollback"),
        )
    if goal == "push":
        return CommandPlan(
            title=tr("planner.push.title"),
            explanation=tr("planner.push.explanation"),
            commands=[["push"]],
            risk=RiskLevel.MEDIUM,
            rollback=tr("planner.push.rollback"),
        )
    if goal == "pull":
        return CommandPlan(
            title=tr("planner.pull.title"),
            explanation=tr("planner.pull.explanation"),
            commands=[["pull", "--ff-only"]],
            risk=RiskLevel.LOW,
            rollback=tr("planner.pull.rollback"),
        )
    if goal == "branch":
        if not value:
            raise ValueError(tr("planner.branch.required"))
        return CommandPlan(
            title=tr("planner.branch.title", name=value),
            explanation=tr("planner.branch.explanation"),
            commands=[["switch", "-c", value]],
            risk=RiskLevel.LOW,
            rollback=tr("planner.branch.rollback", name=value),
        )
    if goal == "undo_commit":
        return CommandPlan(
            title=tr("planner.undo.title"),
            explanation=tr("planner.undo.explanation"),
            commands=[["reset", "--soft", "HEAD~1"]],
            risk=RiskLevel.MEDIUM,
            rollback=tr("planner.undo.rollback"),
        )
    if goal == "recover_file":
        if not value:
            raise ValueError(tr("planner.recover.required"))
        return CommandPlan(
            title=tr("planner.recover.title", path=value),
            explanation=tr("planner.recover.explanation"),
            commands=[["restore", "--", value]],
            risk=RiskLevel.HIGH,
            rollback=tr("planner.recover.rollback"),
        )
    if goal == "conflicts":
        return CommandPlan(
            title=tr("planner.conflicts.title"),
            explanation=tr("planner.conflicts.explanation"),
            commands=[["diff", "--name-only", "--diff-filter=U"]],
            risk=RiskLevel.SAFE,
        )
    raise ValueError(tr("planner.unknown_goal", goal=goal))


def branch_delete_plan(
    name: str,
    *,
    force: bool = False,
    translator: Translator | None = None,
) -> CommandPlan:
    tr = translator or Translator("en")
    name = name.strip()
    if not name:
        raise ValueError(tr("planner.delete.required"))
    return CommandPlan(
        title=tr("planner.delete.title", name=name),
        explanation=tr(
            "planner.delete.force_explanation" if force else "planner.delete.explanation"
        ),
        commands=[["branch", "-D" if force else "-d", name]],
        risk=RiskLevel.CRITICAL if force else RiskLevel.HIGH,
        rollback=tr("planner.delete.rollback"),
    )
