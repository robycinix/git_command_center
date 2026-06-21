from __future__ import annotations

from importlib.resources import files

import yaml
from pydantic import TypeAdapter

from git_command_center.core.models import CommandGuide, RiskLevel
from git_command_center.i18n.translator import Language, resolve_language


class CommandCatalog:
    def __init__(
        self,
        commands: list[CommandGuide] | None = None,
        *,
        language: str = "en",
    ) -> None:
        self.language = resolve_language(language)
        self._commands = (
            commands if commands is not None else self._load_builtin(self.language)
        )

    @staticmethod
    def _load_builtin(language: Language) -> list[CommandGuide]:
        localized = files("git_command_center.data").joinpath(f"commands.{language}.yaml")
        resource = localized if localized.is_file() else files("git_command_center.data").joinpath(
            "commands.en.yaml"
        )
        raw = yaml.safe_load(resource.read_text(encoding="utf-8"))
        return TypeAdapter(list[CommandGuide]).validate_python(raw)

    @property
    def commands(self) -> list[CommandGuide]:
        return list(self._commands)

    @property
    def categories(self) -> list[str]:
        return sorted({command.category for command in self._commands})

    def find(
        self,
        query: str = "",
        *,
        category: str | None = None,
        maximum_risk: RiskLevel | None = None,
    ) -> list[CommandGuide]:
        query = query.casefold().strip()
        risk_order = list(RiskLevel)
        results: list[CommandGuide] = []
        for command in self._commands:
            haystack = " ".join(
                [command.name, command.syntax, command.description, command.category]
            ).casefold()
            if query and query not in haystack:
                continue
            if category and category != "All" and command.category != category:
                continue
            if maximum_risk and risk_order.index(command.risk) > risk_order.index(maximum_risk):
                continue
            results.append(command)
        return results

    def get(self, command_id: str) -> CommandGuide:
        for command in self._commands:
            if command.id == command_id:
                return command
        raise KeyError(command_id)
