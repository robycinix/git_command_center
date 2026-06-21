from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from git import InvalidGitRepositoryError, NoSuchPathError, Repo

from git_command_center.core.models import (
    BranchEntry,
    CommandPlan,
    CommitEntry,
    ExecutionResult,
    FileState,
    ReflogEntry,
    RepositorySnapshot,
)
from git_command_center.core.safety import SafetyPolicy


class RepositoryError(RuntimeError):
    """Raised when repository data cannot be read."""


class GitService:
    def __init__(self, path: Path | str) -> None:
        try:
            self.repo = Repo(Path(path).expanduser(), search_parent_directories=True)
        except (InvalidGitRepositoryError, NoSuchPathError) as error:
            raise RepositoryError(f"No Git repository found from {path}") from error
        if self.repo.working_tree_dir is None:
            raise RepositoryError("Bare repositories are not supported by the TUI.")
        self.path = Path(self.repo.working_tree_dir).resolve()

    def _git(self, *arguments: str) -> str:
        try:
            return self.repo.git.execute(
                ["git", *arguments],
                with_extended_output=False,
                as_process=False,
                stdout_as_string=True,
            )
        except Exception as error:
            raise RepositoryError(str(error)) from error

    def _branch_name(self) -> str:
        if self.repo.head.is_detached:
            try:
                return f"detached@{self.repo.head.commit.hexsha[:8]}"
            except ValueError:
                return "detached"
        try:
            return self.repo.active_branch.name
        except (TypeError, ValueError):
            return "unborn"

    def _files(self) -> list[FileState]:
        output = self._git(
            "-c",
            "core.quotepath=false",
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        )
        files: list[FileState] = []
        for line in output.splitlines():
            if len(line) < 3:
                continue
            path = line[3:]
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            files.append(
                FileState(path=path, index_status=line[0], worktree_status=line[1])
            )
        return files

    def snapshot(self) -> RepositorySnapshot:
        upstream: str | None = None
        ahead = behind = 0
        try:
            upstream = self._git("rev-parse", "--abbrev-ref", "@{upstream}").strip()
            counts = self._git("rev-list", "--left-right", "--count", "HEAD...@{upstream}")
            ahead, behind = (int(value) for value in counts.split())
        except RepositoryError:
            pass

        last_hash: str | None = None
        last_message: str | None = None
        last_author: str | None = None
        last_at: datetime | None = None
        try:
            commit = self.repo.head.commit
            last_hash = commit.hexsha[:8]
            summary = commit.summary
            last_message = (
                summary.decode("utf-8", errors="replace")
                if isinstance(summary, bytes)
                else summary
            )
            author_name = commit.author.name
            last_author = (
                author_name.decode("utf-8", errors="replace")
                if isinstance(author_name, bytes)
                else author_name
            )
            last_at = commit.committed_datetime
        except ValueError:
            pass

        remotes = [f"{remote.name}: {next(iter(remote.urls), '')}" for remote in self.repo.remotes]
        return RepositorySnapshot(
            name=self.path.name,
            path=self.path,
            branch=self._branch_name(),
            remotes=remotes,
            upstream=upstream,
            ahead=ahead,
            behind=behind,
            last_commit_hash=last_hash,
            last_commit_message=last_message,
            last_commit_author=last_author,
            last_commit_at=last_at,
            files=self._files(),
        )

    def commits(self, limit: int = 300, *, all_branches: bool = True) -> list[CommitEntry]:
        separator = "\x1f"
        arguments = [
            "log",
            f"--max-count={limit}",
            f"--format=%h{separator}%an{separator}%aI{separator}%s{separator}%D",
        ]
        if all_branches:
            arguments.append("--all")
        try:
            output = self._git(*arguments)
        except RepositoryError as error:
            if "does not have any commits" in str(error) or "unknown revision" in str(error):
                return []
            raise
        entries: list[CommitEntry] = []
        for line in output.splitlines():
            fields = line.split(separator, 4)
            if len(fields) != 5:
                continue
            entries.append(
                CommitEntry(
                    short_hash=fields[0],
                    author=fields[1],
                    committed_at=datetime.fromisoformat(fields[2]),
                    message=fields[3],
                    decorations=fields[4],
                )
            )
        return entries

    def graph(self, limit: int = 300) -> str:
        try:
            return self._git(
                "log",
                "--graph",
                "--decorate",
                "--all",
                "--date=short",
                f"--max-count={limit}",
                "--pretty=format:%C(auto)%h%Creset %ad %an %d%n    %s",
            )
        except RepositoryError:
            return "No commits yet."

    def branches(self) -> list[BranchEntry]:
        separator = "\x1f"
        format_string = (
            f"%(refname:short){separator}%(HEAD){separator}%(upstream:short)"
            f"{separator}%(objectname:short){separator}%(refname)"
        )
        output = self._git(
            "for-each-ref",
            f"--format={format_string}",
            "refs/heads",
            "refs/remotes",
        )
        entries: list[BranchEntry] = []
        for line in output.splitlines():
            fields = line.split(separator)
            if len(fields) != 5 or fields[0].endswith("/HEAD"):
                continue
            entries.append(
                BranchEntry(
                    name=fields[0],
                    active=fields[1] == "*",
                    remote=fields[4].startswith("refs/remotes/"),
                    tracking=fields[2] or None,
                    commit=fields[3],
                )
            )
        return entries

    def reflog(self, limit: int = 200) -> list[ReflogEntry]:
        separator = "\x1f"
        try:
            output = self._git(
                "reflog",
                f"--max-count={limit}",
                f"--format=%gd{separator}%h{separator}%gs",
            )
        except RepositoryError:
            return []
        entries: list[ReflogEntry] = []
        for line in output.splitlines():
            fields = line.split(separator, 2)
            if len(fields) != 3:
                continue
            action, _, message = fields[2].partition(": ")
            entries.append(
                ReflogEntry(
                    selector=fields[0],
                    short_hash=fields[1],
                    action=action,
                    message=message,
                )
            )
        return entries

    def diff(self, *, staged: bool = False, path: str | None = None) -> str:
        arguments = ["diff", "--no-ext-diff", "--no-color"]
        if staged:
            arguments.append("--cached")
        if path:
            arguments.extend(["--", path])
        return self._git(*arguments) or "No differences to show."

    def execute(
        self,
        plan: CommandPlan,
        *,
        confirmed: bool = False,
        typed_confirmation: str = "",
    ) -> list[ExecutionResult]:
        SafetyPolicy.authorize(
            plan,
            confirmed=confirmed,
            typed_confirmation=typed_confirmation,
        )
        results: list[ExecutionResult] = []
        for arguments in plan.commands:
            process = subprocess.run(
                ["git", *arguments],
                cwd=self.path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            result = ExecutionResult(
                command="git " + " ".join(arguments),
                return_code=process.returncode,
                stdout=process.stdout.strip(),
                stderr=process.stderr.strip(),
            )
            results.append(result)
            if not result.succeeded:
                break
        return results
