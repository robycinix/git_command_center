from __future__ import annotations

from collections.abc import Sequence

from git_command_center.core.models import CommandPlan, RiskLevel


class SafetyError(RuntimeError):
    """Raised when an operation violates the safety policy."""


class SafetyPolicy:
    CRITICAL_CONFIRMATION = "CONFERMO"
    _forbidden_tokens = {";", "&&", "||", "|", ">", ">>", "<"}

    @classmethod
    def validate_arguments(cls, arguments: Sequence[str]) -> None:
        if not arguments:
            raise SafetyError("A Git command cannot be empty.")
        if any(token in cls._forbidden_tokens for token in arguments):
            raise SafetyError("Shell operators are not accepted as Git arguments.")
        if any("\x00" in token or "\n" in token or "\r" in token for token in arguments):
            raise SafetyError("Control characters are not accepted as Git arguments.")

    @classmethod
    def authorize(
        cls,
        plan: CommandPlan,
        *,
        confirmed: bool = False,
        typed_confirmation: str = "",
    ) -> None:
        for command in plan.commands:
            cls.validate_arguments(command)
        if plan.risk in {RiskLevel.HIGH, RiskLevel.CRITICAL} and not confirmed:
            raise SafetyError("This operation requires explicit confirmation.")
        if (
            plan.risk is RiskLevel.CRITICAL
            and typed_confirmation != cls.CRITICAL_CONFIRMATION
        ):
            raise SafetyError('Type "CONFERMO" to authorize this critical operation.')
