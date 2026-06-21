from __future__ import annotations

import pytest

from git_command_center.core.models import CommandPlan, RiskLevel
from git_command_center.core.safety import SafetyError, SafetyPolicy


def test_critical_plan_requires_both_confirmations() -> None:
    plan = CommandPlan(
        title="Reset",
        explanation="Discard work",
        commands=[["reset", "--hard", "HEAD"]],
        risk=RiskLevel.CRITICAL,
    )

    with pytest.raises(SafetyError):
        SafetyPolicy.authorize(plan)
    with pytest.raises(SafetyError):
        SafetyPolicy.authorize(plan, confirmed=True)

    SafetyPolicy.authorize(plan, confirmed=True, typed_confirmation="CONFERMO")


@pytest.mark.parametrize("operator", [";", "&&", "|", ">"])
def test_shell_operators_are_rejected(operator: str) -> None:
    plan = CommandPlan(
        title="Bad",
        explanation="Bad",
        commands=[["status", operator, "echo"]],
    )
    with pytest.raises(SafetyError):
        SafetyPolicy.authorize(plan)
