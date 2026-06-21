from __future__ import annotations

from git_command_center.core.models import CommandPlan, RiskLevel

GOALS: dict[str, str] = {
    "save": "Save changes in a commit",
    "push": "Send commits to the remote",
    "pull": "Download remote updates safely",
    "branch": "Create and switch to a branch",
    "undo_commit": "Undo the latest commit but keep its changes",
    "recover_file": "Discard local edits in one file",
    "conflicts": "Inspect unresolved conflicts",
}


def build_plan(goal: str, *, value: str = "") -> CommandPlan:
    value = value.strip()
    if goal == "save":
        message = value or "Describe your changes"
        return CommandPlan(
            title="Save all current changes",
            explanation="Stage tracked and untracked files, then create one commit.",
            commands=[["add", "--all"], ["commit", "-m", message]],
            risk=RiskLevel.LOW,
            rollback="git reset --soft HEAD~1 keeps the changes while removing the commit.",
        )
    if goal == "push":
        return CommandPlan(
            title="Send local commits",
            explanation="Push the active branch to its configured upstream.",
            commands=[["push"]],
            risk=RiskLevel.MEDIUM,
            rollback="Published commits require a follow-up revert in shared branches.",
        )
    if goal == "pull":
        return CommandPlan(
            title="Download remote updates",
            explanation="Fetch and fast-forward only; no surprise merge commit is created.",
            commands=[["pull", "--ff-only"]],
            risk=RiskLevel.LOW,
            rollback="Use reflog to locate the previous HEAD if needed.",
        )
    if goal == "branch":
        if not value:
            raise ValueError("Enter the new branch name.")
        return CommandPlan(
            title=f"Create branch {value}",
            explanation="Create a new branch at HEAD and switch to it.",
            commands=[["switch", "-c", value]],
            risk=RiskLevel.LOW,
            rollback=f"Switch away, then run git branch -d {value}.",
        )
    if goal == "undo_commit":
        return CommandPlan(
            title="Undo the latest local commit",
            explanation="Move HEAD back once while leaving every change staged.",
            commands=[["reset", "--soft", "HEAD~1"]],
            risk=RiskLevel.MEDIUM,
            rollback="The removed commit remains available in reflog.",
        )
    if goal == "recover_file":
        if not value:
            raise ValueError("Enter the repository-relative file path.")
        return CommandPlan(
            title=f"Discard edits in {value}",
            explanation="Restore the working-tree file from the index.",
            commands=[["restore", "--", value]],
            risk=RiskLevel.HIGH,
            rollback="Uncommitted edits may not be recoverable.",
        )
    if goal == "conflicts":
        return CommandPlan(
            title="List unresolved conflicts",
            explanation="Show only files with unresolved merge entries; it changes nothing.",
            commands=[["diff", "--name-only", "--diff-filter=U"]],
            risk=RiskLevel.SAFE,
        )
    raise ValueError(f"Unknown goal: {goal}")


def branch_delete_plan(name: str, *, force: bool = False) -> CommandPlan:
    name = name.strip()
    if not name:
        raise ValueError("Enter a branch name.")
    return CommandPlan(
        title=f"Delete branch {name}",
        explanation=(
            "Force-delete the local branch even when it is not merged."
            if force
            else "Delete the local branch only if it has already been merged."
        ),
        commands=[["branch", "-D" if force else "-d", name]],
        risk=RiskLevel.CRITICAL if force else RiskLevel.HIGH,
        rollback="Find the previous branch tip in reflog and recreate the branch there.",
    )
