from __future__ import annotations

import pytest

from git_command_center.core.models import RiskLevel
from git_command_center.services.catalog import CommandCatalog
from git_command_center.services.planner import branch_delete_plan, build_plan


def test_catalog_filters_by_text_category_and_risk() -> None:
    catalog = CommandCatalog()
    matches = catalog.find("reset", category="Recovery", maximum_risk=RiskLevel.CRITICAL)
    assert [command.id for command in matches] == ["reset-hard"]
    assert catalog.find(maximum_risk=RiskLevel.SAFE)
    safe_commands = catalog.find(maximum_risk=RiskLevel.SAFE)
    assert all(command.risk is RiskLevel.SAFE for command in safe_commands)


def test_save_plan_preserves_message_as_single_argument() -> None:
    plan = build_plan("save", value="Explain the change")
    assert plan.commands[-1] == ["commit", "-m", "Explain the change"]
    assert plan.risk is RiskLevel.LOW


def test_branch_name_is_required() -> None:
    with pytest.raises(ValueError):
        build_plan("branch")


def test_force_branch_delete_is_critical() -> None:
    assert branch_delete_plan("topic", force=True).risk is RiskLevel.CRITICAL
