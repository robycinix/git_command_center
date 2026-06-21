from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.markup import escape
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Markdown,
    RichLog,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from git_command_center.config.settings import (
    AppSettings,
    default_config_path,
    save_settings,
)
from git_command_center.core.models import CommandGuide, CommandPlan, RepositorySnapshot, RiskLevel
from git_command_center.git.service import GitService, RepositoryError
from git_command_center.i18n import SUPPORTED_LANGUAGES, Translator
from git_command_center.services.catalog import CommandCatalog
from git_command_center.services.path_setup import (
    PathSetupError,
    PathSetupStatus,
    setup_user_path,
)
from git_command_center.services.planner import GOALS, branch_delete_plan, build_plan
from git_command_center.services.platform import open_directory
from git_command_center.services.simulation import SimulationService


class ConfirmScreen(ModalScreen[tuple[bool, str]]):
    def __init__(self, plan: CommandPlan, translator: Translator) -> None:
        super().__init__()
        self.plan = plan
        self.tr = translator

    def compose(self) -> ComposeResult:
        critical = self.plan.risk is RiskLevel.CRITICAL
        command_list = "\n".join(self.plan.display_commands)
        with Vertical(id="confirm-dialog"):
            yield Static(
                f"[bold]{escape(self.tr('confirm.title', title=self.plan.title))}[/bold]"
            )
            yield Static(
                f"{self.tr('confirm.risk')}: "
                f"[bold]{self.tr(f'risk.{self.plan.risk.value}')}[/bold]\n\n"
                f"{escape(self.plan.explanation)}\n\n[cyan]{escape(command_list)}[/cyan]"
            )
            if critical:
                yield Static(self.tr("confirm.critical_prompt"))
                yield Input(placeholder="CONFERMO", id="typed-confirmation")
            with Horizontal(id="confirm-buttons"):
                yield Button(self.tr("confirm.cancel"), id="cancel-confirm")
                yield Button(self.tr("confirm.execute"), id="accept-confirm", variant="warning")

    @on(Button.Pressed, "#cancel-confirm")
    def cancel(self) -> None:
        self.dismiss((False, ""))

    @on(Button.Pressed, "#accept-confirm")
    def accept(self) -> None:
        typed = ""
        if self.plan.risk is RiskLevel.CRITICAL:
            typed = self.query_one("#typed-confirmation", Input).value
        self.dismiss((True, typed))


class GCCApp(App[None]):
    TITLE = "Git Command Center"
    SUB_TITLE = ""
    CSS_PATH = "../themes/gcc.tcss"
    BINDINGS = [
        Binding("q", "quit", "Quit", show=False),
        Binding("r", "refresh_repository", "Refresh", show=False),
        Binding("f1", "show_help", "Help", show=False),
    ]

    def __init__(
        self,
        service: GitService,
        settings: AppSettings,
        translator: Translator | None = None,
    ) -> None:
        super().__init__()
        self.service = service
        self.settings = settings
        self.tr = translator or Translator(settings.language)
        self.sub_title = self.tr("app.subtitle")
        self.catalog = CommandCatalog(language=self.tr.language)
        self.current_plan: CommandPlan | None = None
        self.sandbox_path: Path | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(self.tr("loading.repository"), id="repo-strip")
        with TabbedContent(initial="dashboard"):
            with TabPane(self.tr("tab.dashboard"), id="dashboard"):
                yield Markdown(id="dashboard-content")
            with TabPane(self.tr("tab.commands"), id="commands"):
                with Horizontal(classes="toolbar"):
                    yield Input(placeholder=self.tr("filter.search"), id="command-search")
                    yield Select(
                        [(self.tr("filter.all_categories"), "All")]
                        + [
                            (self._category_label(category), category)
                            for category in self.catalog.categories
                        ],
                        value="All",
                        allow_blank=False,
                        id="command-category",
                    )
                    yield Select(
                        [
                            (self.tr("filter.any_risk"), "all"),
                            (self.tr("filter.up_to_low"), "low"),
                            (self.tr("filter.up_to_medium"), "medium"),
                            (self.tr("filter.safe_only"), "safe"),
                        ],
                        value="all",
                        allow_blank=False,
                        id="command-risk",
                    )
                with Horizontal():
                    yield DataTable(id="command-table", classes="split-left")
                    yield Markdown(id="command-details", classes="split-right")
            with TabPane(self.tr("tab.wizard"), id="wizard"):
                yield Static(self.tr("wizard.hint"), classes="hint")
                with Horizontal(classes="toolbar"):
                    yield Select(
                        [(self.tr(f"goal.{key}"), key) for key in GOALS],
                        value="save",
                        allow_blank=False,
                        id="goal-select",
                    )
                    yield Input(
                        placeholder=self.tr("wizard.value_placeholder"),
                        id="goal-value",
                    )
                    yield Button(self.tr("wizard.build"), id="build-plan", variant="primary")
                    yield Button(
                        self.tr("wizard.execute"), id="execute-plan", variant="success"
                    )
                yield Markdown(self.tr("wizard.no_plan"), id="plan-preview")
                yield Static("", id="operation-output")
            with TabPane(self.tr("tab.history"), id="history"):
                yield Static(self.tr("history.hint"), classes="hint")
                yield RichLog(highlight=True, markup=False, wrap=False, id="history-log")
            with TabPane(self.tr("tab.branches"), id="branches"):
                with Horizontal(classes="toolbar"):
                    yield Input(placeholder=self.tr("branch.name_placeholder"), id="branch-name")
                    yield Button(self.tr("branch.create"), id="create-branch", variant="primary")
                    yield Button(self.tr("branch.checkout"), id="checkout-branch")
                    yield Button(self.tr("branch.delete"), id="delete-branch", variant="warning")
                yield DataTable(id="branch-table")
            with TabPane(self.tr("tab.diff"), id="diff"):
                with Horizontal(classes="toolbar"):
                    yield Input(placeholder=self.tr("diff.path_placeholder"), id="diff-path")
                    yield Checkbox(self.tr("diff.staged"), id="diff-staged")
                    yield Button(self.tr("diff.refresh"), id="refresh-diff", variant="primary")
                yield RichLog(highlight=True, markup=False, wrap=False, id="diff-log")
            with TabPane(self.tr("tab.recovery"), id="recovery"):
                yield Static(self.tr("recovery.hint"), classes="hint")
                yield DataTable(id="reflog-table")
            with TabPane(self.tr("tab.learn"), id="learn"):
                with Horizontal(classes="toolbar"):
                    yield Select(
                        [
                            (self.tr("learn.beginner"), "beginner"),
                            (self.tr("learn.intermediate"), "intermediate"),
                            (self.tr("learn.advanced"), "advanced"),
                            (self.tr("learn.expert"), "expert"),
                        ],
                        value="beginner",
                        allow_blank=False,
                        id="lesson-select",
                    )
                    yield Button(
                        self.tr("learn.create_sandbox"),
                        id="create-sandbox",
                        variant="primary",
                    )
                    yield Button(
                        self.tr("learn.open_sandbox"),
                        id="open-sandbox",
                        disabled=True,
                    )
                yield Markdown(self.tr("lesson.beginner"), id="lesson-content")
                yield Static("", id="sandbox-path")
            with TabPane(self.tr("tab.settings"), id="settings"):
                yield Markdown(f"# {self.tr('settings.title')}")
                yield Static(self.tr("settings.language"), classes="hint")
                yield Select(
                    [(self.tr("language.auto"), "auto")]
                    + [
                        (self.tr(f"language.{language}"), language)
                        for language in SUPPORTED_LANGUAGES
                    ],
                    value=self.settings.language,
                    allow_blank=False,
                    id="settings-language",
                )
                yield Button(self.tr("settings.save"), id="save-settings", variant="primary")
                yield Static(
                    self.tr("settings.current_file", path=default_config_path()),
                    classes="hint",
                )
                yield Static(self.tr("settings.restart_hint"), classes="hint")
                yield Markdown(f"## {self.tr('settings.terminal_title')}")
                yield Static(self.tr("settings.terminal_description"), classes="hint")
                yield Button(
                    self.tr("settings.terminal_button"),
                    id="setup-path",
                    variant="success",
                )
                yield Static("", id="path-status", classes="hint")
        yield Footer()

    def on_mount(self) -> None:
        theme_names = {"dark": "textual-dark", "light": "textual-light"}
        requested_theme = theme_names.get(self.settings.theme, self.settings.theme)
        if requested_theme in self.available_themes:
            self.theme = requested_theme
        custom_actions = {
            "refresh": ("refresh_repository", self.tr("binding.refresh")),
            "quit": ("quit", self.tr("binding.quit")),
            "help": ("show_help", self.tr("binding.help")),
        }
        for name, key in self.settings.shortcuts.items():
            if name in custom_actions and key:
                action, description = custom_actions[name]
                self.bind(key, action, description=description)

        command_table = self.query_one("#command-table", DataTable)
        command_table.add_columns(
            self.tr("table.command"),
            self.tr("table.category"),
            self.tr("table.risk"),
        )
        command_table.cursor_type = "row"
        branch_table = self.query_one("#branch-table", DataTable)
        branch_table.add_columns(
            "",
            self.tr("table.branch"),
            self.tr("table.type"),
            self.tr("table.tracking"),
            self.tr("table.commit"),
        )
        branch_table.cursor_type = "row"
        reflog_table = self.query_one("#reflog-table", DataTable)
        reflog_table.add_columns(
            self.tr("table.selector"),
            self.tr("table.hash"),
            self.tr("table.action"),
            self.tr("table.message"),
        )
        reflog_table.cursor_type = "row"
        self._refresh_command_table()
        self.action_refresh_repository()
        self.set_interval(self.settings.refresh_interval, self.action_refresh_repository)

    def action_show_help(self) -> None:
        self.notify(
            self.tr("help.body"),
            title=self.tr("help.title"),
            timeout=8,
        )

    def action_refresh_repository(self) -> None:
        self._load_repository_data()

    @work(thread=True, exclusive=True, group="repository-refresh")
    def _load_repository_data(self) -> None:
        try:
            snapshot = self.service.snapshot()
            graph = self.service.graph(self.settings.history_limit)
            branches = self.service.branches()
            reflog = self.service.reflog()
            diff = self.service.diff()
        except RepositoryError as error:
            self.call_from_thread(self.notify, str(error), severity="error")
            return
        self.call_from_thread(
            self._apply_repository_data,
            snapshot,
            graph,
            branches,
            reflog,
            diff,
        )

    def _apply_repository_data(
        self,
        snapshot: RepositorySnapshot,
        graph: str,
        branches: list[Any],
        reflog: list[Any],
        diff: str,
    ) -> None:
        remote_text = " | ".join(snapshot.remotes) or self.tr("repo.no_remote")
        sync_label = self._sync_label(snapshot)
        self.query_one("#repo-strip", Static).update(
            f"[bold]{escape(snapshot.name)}[/bold]  {escape(str(snapshot.path))}\n"
            f"{self.tr('repo.branch')}: [cyan]{escape(snapshot.branch)}[/cyan]  |  "
            f"{self.tr('repo.sync')}: {escape(sync_label)}  |  "
            f"{self.tr('repo.remote')}: {escape(remote_text)}"
        )
        last_commit = self.tr("repo.no_commit")
        if snapshot.last_commit_at is not None:
            last_commit = (
                f"`{snapshot.last_commit_hash}` {snapshot.last_commit_message}\n"
                f"{self.tr('repo.author')}: **{snapshot.last_commit_author}** - "
                f"{self._elapsed(snapshot.last_commit_at)}"
            )
        dashboard = (
            f"# {self.tr('dashboard.title')}\n\n"
            f"**{self.tr('dashboard.path')}:** `{snapshot.path}`\n\n"
            f"**{self.tr('dashboard.active_branch')}:** `{snapshot.branch}`\n"
            f"**{self.tr('dashboard.upstream')}:** "
            f"`{snapshot.upstream or self.tr('repo.not_configured')}`\n"
            f"**{self.tr('dashboard.synchronization')}:** {sync_label}\n\n"
            f"## {self.tr('dashboard.worktree')}\n\n"
            f"- {self.tr('dashboard.modified_files', count=snapshot.modified_count)}\n"
            f"- {self.tr('dashboard.staged_files', count=snapshot.staged_count)}\n"
            f"- {self.tr('dashboard.untracked_files', count=snapshot.untracked_count)}\n"
            f"- {self.tr('dashboard.commits_ahead', count=snapshot.ahead)}\n"
            f"- {self.tr('dashboard.commits_behind', count=snapshot.behind)}\n\n"
            f"## {self.tr('dashboard.last_commit')}\n\n{last_commit}\n\n"
            f"## {self.tr('dashboard.remotes')}\n\n{remote_text}"
        )
        self.query_one("#dashboard-content", Markdown).update(dashboard)

        history_log = self.query_one("#history-log", RichLog)
        history_log.clear()
        history_log.write(Text.from_ansi(graph))

        branch_table = self.query_one("#branch-table", DataTable)
        branch_table.clear(columns=False)
        for branch in branches:
            branch_table.add_row(
                "*" if branch.active else "",
                branch.name,
                self.tr("branch.type_remote" if branch.remote else "branch.type_local"),
                branch.tracking or "-",
                branch.commit,
                key=branch.name,
            )

        reflog_table = self.query_one("#reflog-table", DataTable)
        reflog_table.clear(columns=False)
        for entry in reflog:
            reflog_table.add_row(
                entry.selector,
                entry.short_hash,
                entry.action,
                entry.message,
                key=entry.selector,
            )

        self._write_log("#diff-log", diff)

    def _sync_label(self, snapshot: RepositorySnapshot) -> str:
        if snapshot.upstream is None:
            return self.tr("sync.no_upstream")
        if snapshot.ahead == 0 and snapshot.behind == 0:
            return self.tr("sync.synchronized")
        return self.tr("sync.diverged", ahead=snapshot.ahead, behind=snapshot.behind)

    def _elapsed(self, value: datetime) -> str:
        now = datetime.now(UTC)
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        seconds = max(0, int((now - value.astimezone(UTC)).total_seconds()))
        if seconds < 60:
            return self.tr("time.less_than_minute")
        if seconds < 3600:
            return self.tr("time.minutes", count=seconds // 60)
        if seconds < 86_400:
            return self.tr("time.hours", count=seconds // 3600)
        return self.tr("time.days", count=seconds // 86_400)

    def _category_label(self, category: str) -> str:
        return self.tr(f"category.{category.casefold()}")

    def _risk_label(self, risk: RiskLevel) -> str:
        return self.tr(f"risk.{risk.value}")

    def _refresh_command_table(self) -> None:
        query = self.query_one("#command-search", Input).value
        category_value = self.query_one("#command-category", Select).value
        risk_value = self.query_one("#command-risk", Select).value
        category = str(category_value)
        maximum_risk = None if risk_value == "all" else RiskLevel(str(risk_value))
        commands = self.catalog.find(
            query,
            category=category,
            maximum_risk=maximum_risk,
        )
        table = self.query_one("#command-table", DataTable)
        table.clear(columns=False)
        for command in commands:
            table.add_row(
                command.name,
                self._category_label(command.category),
                self._risk_label(command.risk),
                key=command.id,
            )
        if commands:
            self._show_command(commands[0])

    @on(Input.Changed, "#command-search")
    @on(Select.Changed, "#command-category")
    @on(Select.Changed, "#command-risk")
    def command_filters_changed(self) -> None:
        self._refresh_command_table()

    @on(DataTable.RowSelected, "#command-table")
    def command_selected(self, event: DataTable.RowSelected) -> None:
        self._show_command(self.catalog.get(str(event.row_key.value)))

    def _show_command(self, command: CommandGuide) -> None:
        errors = (
            "\n".join(f"- {item}" for item in command.common_errors)
            or f"- {self.tr('command.no_errors')}"
        )
        rollback = command.rollback or self.tr("command.no_rollback")
        alternative = (
            f"\n\n## {self.tr('command.alternative')}\n\n"
            f"{command.recommended_alternative}"
            if command.recommended_alternative
            else ""
        )
        content = f"""# {command.name}

**{self.tr("command.syntax")}:** `{command.syntax}`
**{self.tr("command.category")}:** {self._category_label(command.category)}
**{self.tr("command.risk")}:** **{self._risk_label(command.risk)}**

## {self.tr("command.description")}

{command.description}

**{self.tr("command.use_when")}** {command.use_when}
**{self.tr("command.avoid_when")}** {command.avoid_when}

**{self.tr("command.example")}:** `{command.example}`

## {self.tr("command.common_errors")}

{errors}

## {self.tr("command.consequences")}

{command.consequences}

**{self.tr("command.rollback")}:** {rollback}{alternative}
"""
        self.query_one("#command-details", Markdown).update(content)

    @on(Button.Pressed, "#build-plan")
    def build_wizard_plan(self) -> None:
        goal = str(self.query_one("#goal-select", Select).value)
        value = self.query_one("#goal-value", Input).value
        try:
            self._set_plan(build_plan(goal, value=value, translator=self.tr))
        except ValueError as error:
            self.notify(str(error), severity="warning")

    def _set_plan(self, plan: CommandPlan) -> None:
        self.current_plan = plan
        commands = "\n".join(f"1. `{command}`" for command in plan.display_commands)
        rollback = plan.rollback or self.tr("plan.no_rollback")
        self.query_one("#plan-preview", Markdown).update(
            f"# {plan.title}\n\n{plan.explanation}\n\n"
            f"**{self.tr('plan.risk')}:** {self._risk_label(plan.risk)}\n\n"
            f"## {self.tr('plan.commands')}\n\n{commands}\n\n"
            f"**{self.tr('plan.rollback')}:** {rollback}"
        )

    @on(Button.Pressed, "#execute-plan")
    def execute_current_plan(self) -> None:
        if self.current_plan is None:
            self.notify(self.tr("error.plan_first"), severity="warning")
            return
        self._request_execution(self.current_plan)

    @on(Button.Pressed, "#create-branch")
    def create_branch(self) -> None:
        name = self.query_one("#branch-name", Input).value
        try:
            plan = build_plan("branch", value=name, translator=self.tr)
        except ValueError as error:
            self.notify(str(error), severity="warning")
            return
        self._set_plan(plan)
        self._request_execution(plan)

    @on(Button.Pressed, "#checkout-branch")
    def checkout_branch(self) -> None:
        name = self.query_one("#branch-name", Input).value.strip()
        if not name:
            self.notify(self.tr("error.branch_name"), severity="warning")
            return
        plan = CommandPlan(
            title=self.tr("planner.checkout.title", name=name),
            explanation=self.tr("planner.checkout.explanation"),
            commands=[["switch", name]],
            risk=RiskLevel.LOW,
            rollback=self.tr("planner.checkout.rollback"),
        )
        self._request_execution(plan)

    @on(Button.Pressed, "#delete-branch")
    def delete_branch(self) -> None:
        name = self.query_one("#branch-name", Input).value
        try:
            self._request_execution(branch_delete_plan(name, translator=self.tr))
        except ValueError as error:
            self.notify(str(error), severity="warning")

    @on(DataTable.RowSelected, "#branch-table")
    def branch_selected(self, event: DataTable.RowSelected) -> None:
        self.query_one("#branch-name", Input).value = str(event.row_key.value)

    @on(Button.Pressed, "#refresh-diff")
    def refresh_diff(self) -> None:
        path = self.query_one("#diff-path", Input).value.strip() or None
        staged = self.query_one("#diff-staged", Checkbox).value
        self._load_diff(path, staged)

    @work(thread=True, exclusive=True, group="diff-refresh")
    def _load_diff(self, path: str | None, staged: bool) -> None:
        try:
            diff = self.service.diff(path=path, staged=staged)
        except RepositoryError as error:
            self.call_from_thread(self.notify, str(error), severity="error")
            return
        self.call_from_thread(self._write_log, "#diff-log", diff)

    def _write_log(self, selector: str, content: str) -> None:
        log = self.query_one(selector, RichLog)
        log.clear()
        log.write(Text.from_ansi(content))

    @on(Select.Changed, "#lesson-select")
    def lesson_changed(self, event: Select.Changed) -> None:
        value = str(event.value)
        if value in {"beginner", "intermediate", "advanced", "expert"}:
            self.query_one("#lesson-content", Markdown).update(self.tr(f"lesson.{value}"))

    @on(Button.Pressed, "#create-sandbox")
    def create_sandbox(self) -> None:
        self._create_sandbox_worker()

    @work(thread=True, exclusive=True, group="sandbox")
    def _create_sandbox_worker(self) -> None:
        try:
            path = SimulationService().create()
        except (OSError, subprocess.SubprocessError) as error:
            self.call_from_thread(self.notify, str(error), severity="error")
            return
        self.call_from_thread(
            self._sandbox_ready,
            path,
        )

    def _sandbox_ready(self, path: Path) -> None:
        self.sandbox_path = path
        self.query_one("#sandbox-path", Static).update(
            self.tr("sandbox.ready", path=escape(str(path)))
        )
        self.query_one("#open-sandbox", Button).disabled = False

    @on(Button.Pressed, "#open-sandbox")
    def open_sandbox(self) -> None:
        if self.sandbox_path is None:
            self.notify(self.tr("sandbox.not_ready"), severity="warning")
            return
        try:
            open_directory(self.sandbox_path)
        except OSError as error:
            self.notify(str(error), severity="error")
            return
        self.notify(self.tr("sandbox.opened"))

    @on(Button.Pressed, "#save-settings")
    def save_preferences(self) -> None:
        language = str(self.query_one("#settings-language", Select).value)
        self.settings = AppSettings.model_validate(
            {**self.settings.model_dump(), "language": language}
        )
        save_settings(self.settings)
        self.notify(self.tr("settings.saved"), title=self.tr("tab.settings"))

    @on(Button.Pressed, "#setup-path")
    def setup_terminal_command(self) -> None:
        try:
            result = setup_user_path()
        except PathSetupError:
            message = self.tr("path_setup.missing")
            self.query_one("#path-status", Static).update(escape(message))
            self.notify(message, severity="error")
            return

        message_key = (
            "path_setup.already"
            if result.status is PathSetupStatus.ALREADY_PRESENT
            else "path_setup.added"
        )
        message = self.tr(message_key, path=result.scripts_directory)
        if result.status is PathSetupStatus.ADDED:
            message = f"{message}\n{self.tr('path_setup.reopen')}"
        self.query_one("#path-status", Static).update(escape(message))
        self.notify(message, title=self.tr("settings.terminal_title"))

    def _request_execution(self, plan: CommandPlan) -> None:
        if plan.risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            self.push_screen(
                ConfirmScreen(plan, self.tr),
                lambda answer: self._confirmed(plan, answer),
            )
        else:
            self._execute_plan(plan, False, "")

    def _confirmed(self, plan: CommandPlan, answer: tuple[bool, str]) -> None:
        accepted, typed = answer
        if accepted:
            self._execute_plan(plan, True, typed)

    @work(thread=True, exclusive=True, group="command-execution")
    def _execute_plan(self, plan: CommandPlan, confirmed: bool, typed: str) -> None:
        try:
            results = self.service.execute(
                plan,
                confirmed=confirmed,
                typed_confirmation=typed,
            )
        except (RepositoryError, RuntimeError) as error:
            self.call_from_thread(self._show_operation_error, str(error))
            return
        self.call_from_thread(self._show_results, results)

    def _show_operation_error(self, message: str) -> None:
        self.query_one("#operation-output", Static).update(
            f"[bold red]{self.tr('error.operation_blocked')}[/bold red]\n{escape(message)}"
        )
        self.notify(message, severity="error")

    def _show_results(self, results: list[Any]) -> None:
        lines: list[str] = []
        succeeded = True
        for result in results:
            marker = self.tr("result.ok" if result.succeeded else "result.error")
            lines.append(f"[{marker}] {result.command}")
            if result.stdout:
                lines.append(result.stdout)
            if result.stderr:
                lines.append(result.stderr)
            succeeded = succeeded and result.succeeded
        self.query_one("#operation-output", Static).update(escape("\n".join(lines)))
        self.notify(
            self.tr("result.completed" if succeeded else "result.failed"),
            severity="information" if succeeded else "error",
        )
        self.action_refresh_repository()
