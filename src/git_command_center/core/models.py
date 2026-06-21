from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FileState(BaseModel):
    path: str
    index_status: str = " "
    worktree_status: str = " "

    @property
    def staged(self) -> bool:
        return self.index_status not in {" ", "?"}

    @property
    def untracked(self) -> bool:
        return self.index_status == "?" and self.worktree_status == "?"


class RepositorySnapshot(BaseModel):
    name: str
    path: Path
    branch: str
    remotes: list[str] = Field(default_factory=list)
    upstream: str | None = None
    ahead: int = 0
    behind: int = 0
    last_commit_hash: str | None = None
    last_commit_message: str | None = None
    last_commit_author: str | None = None
    last_commit_at: datetime | None = None
    files: list[FileState] = Field(default_factory=list)

    @property
    def modified_count(self) -> int:
        return sum(not item.untracked for item in self.files)

    @property
    def staged_count(self) -> int:
        return sum(item.staged for item in self.files)

    @property
    def untracked_count(self) -> int:
        return sum(item.untracked for item in self.files)

    @property
    def sync_label(self) -> str:
        if self.upstream is None:
            return "No upstream"
        if self.ahead == 0 and self.behind == 0:
            return "Synchronized"
        return f"{self.ahead} ahead / {self.behind} behind"


class CommitEntry(BaseModel):
    short_hash: str
    author: str
    committed_at: datetime
    message: str
    decorations: str = ""
    graph: str = ""


class BranchEntry(BaseModel):
    name: str
    active: bool = False
    remote: bool = False
    tracking: str | None = None
    commit: str = ""


class ReflogEntry(BaseModel):
    selector: str
    short_hash: str
    action: str
    message: str


class CommandGuide(BaseModel):
    id: str
    name: str
    syntax: str
    category: str
    description: str
    use_when: str
    avoid_when: str
    example: str
    risk: RiskLevel
    common_errors: list[str] = Field(default_factory=list)
    consequences: str
    rollback: str | None = None
    recommended_alternative: str | None = None


class CommandPlan(BaseModel):
    title: str
    explanation: str
    commands: list[list[str]]
    risk: RiskLevel = RiskLevel.LOW
    rollback: str | None = None
    requires_clean_worktree: bool = False

    @property
    def display_commands(self) -> list[str]:
        return ["git " + " ".join(command) for command in self.commands]


class ExecutionResult(BaseModel):
    command: str
    return_code: int
    stdout: str = ""
    stderr: str = ""

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0
