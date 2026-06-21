from __future__ import annotations

from typing import Protocol

from git_command_center.core.models import RepositorySnapshot


class AIProvider(Protocol):
    @property
    def name(self) -> str: ...

    def explain_error(self, error: str, snapshot: RepositorySnapshot) -> str: ...

    def suggest_commit_message(self, diff: str) -> str: ...

    def summarize_changes(self, diff: str) -> str: ...


class DisabledAIProvider:
    name = "disabled"

    def _message(self) -> str:
        return "AI is disabled. Repository data has not left this computer."

    def explain_error(self, error: str, snapshot: RepositorySnapshot) -> str:
        return self._message()

    def suggest_commit_message(self, diff: str) -> str:
        return self._message()

    def summarize_changes(self, diff: str) -> str:
        return self._message()
