from __future__ import annotations

import subprocess
from datetime import UTC, datetime
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

from git_command_center.config.settings import AppSettings
from git_command_center.core.models import CommandGuide, CommandPlan, RepositorySnapshot, RiskLevel
from git_command_center.git.service import GitService, RepositoryError
from git_command_center.services.catalog import CommandCatalog
from git_command_center.services.planner import GOALS, branch_delete_plan, build_plan
from git_command_center.services.simulation import SimulationService

LESSONS: dict[str, str] = {
    "beginner": """# Principiante: le tre aree di Git

Git conserva il lavoro in tre aree: **worktree**, **staging area** e **repository**.

1. Modifica un file nel worktree.
2. Selezionalo con `git add`.
3. Crea una snapshot con `git commit`.

## Quiz

`git add` pubblica il file online? **No**: prepara solo il prossimo commit locale.

## Esercizio

Nella sandbox modifica `README.md`, controlla `git status`, aggiungi il file e crea un commit.
""",
    "intermediate": """# Intermedio: branch e integrazione

Un branch e un riferimento mobile a un commit. Crea branch piccoli e con uno scopo chiaro.

## Quiz

Su quale branch devi trovarti prima di `git merge feature`? Sul branch che deve ricevere il lavoro.

## Esercizio

Crea `feature/demo`, aggiungi un commit, torna su `main` ed esegui il merge.
""",
    "advanced": """# Avanzato: rebase e reflog

Il rebase riscrive i commit. Usalo su lavoro locale, non su cronologia condivisa. Il reflog
registra gli spostamenti dei riferimenti locali e spesso permette di ritrovare un commit perso.

## Quiz

Perche gli hash cambiano dopo un rebase? Perche cambiano i parent e quindi il contenuto del commit.

## Esercizio

Crea due branch divergenti nella sandbox, esegui un rebase e confronta `git log --graph --all`.
""",
    "expert": """# Esperto: collaborazione e recovery

Prima di modificare una cronologia pubblicata, identifica proprietari, branch protetti e
strategia di rollback. Preferisci `--force-with-lease` a `--force`, solo su branch personali.

## Quiz

Cosa protegge `--force-with-lease`? Impedisce la sovrascrittura se il riferimento remoto e cambiato
rispetto all'ultima conoscenza locale.

## Esercizio

Simula un reset, individua il vecchio commit nel reflog e ricrea un branch che lo punti.
""",
}


class ConfirmScreen(ModalScreen[tuple[bool, str]]):
    def __init__(self, plan: CommandPlan) -> None:
        super().__init__()
        self.plan = plan

    def compose(self) -> ComposeResult:
        critical = self.plan.risk is RiskLevel.CRITICAL
        command_list = "\n".join(self.plan.display_commands)
        with Vertical(id="confirm-dialog"):
            yield Static(f"[bold]Conferma: {escape(self.plan.title)}[/bold]")
            yield Static(
                f"Rischio: [bold]{self.plan.risk.value.upper()}[/bold]\n\n"
                f"{escape(self.plan.explanation)}\n\n[cyan]{escape(command_list)}[/cyan]"
            )
            if critical:
                yield Static('Seconda conferma richiesta: digita "CONFERMO".')
                yield Input(placeholder="CONFERMO", id="typed-confirmation")
            with Horizontal(id="confirm-buttons"):
                yield Button("Annulla", id="cancel-confirm")
                yield Button("Esegui", id="accept-confirm", variant="warning")

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
    SUB_TITLE = "Git visibile, guidato e sicuro"
    CSS_PATH = "../themes/gcc.tcss"
    BINDINGS = [
        Binding("q", "quit", "Esci"),
        Binding("r", "refresh_repository", "Aggiorna"),
        Binding("f1", "show_help", "Aiuto"),
    ]

    def __init__(self, service: GitService, settings: AppSettings) -> None:
        super().__init__()
        self.service = service
        self.settings = settings
        self.catalog = CommandCatalog()
        self.current_plan: CommandPlan | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("Caricamento repository...", id="repo-strip")
        with TabbedContent(initial="dashboard"):
            with TabPane("Dashboard", id="dashboard"):
                yield Markdown(id="dashboard-content")
            with TabPane("Comandi", id="commands"):
                with Horizontal(classes="toolbar"):
                    yield Input(placeholder="Ricerca live...", id="command-search")
                    yield Select(
                        [("Tutte le categorie", "All")]
                        + [(category, category) for category in self.catalog.categories],
                        value="All",
                        allow_blank=False,
                        id="command-category",
                    )
                    yield Select(
                        [
                            ("Qualsiasi rischio", "all"),
                            ("Fino a basso", "low"),
                            ("Fino a medio", "medium"),
                            ("Solo operazioni sicure", "safe"),
                        ],
                        value="all",
                        allow_blank=False,
                        id="command-risk",
                    )
                with Horizontal():
                    yield DataTable(id="command-table", classes="split-left")
                    yield Markdown(id="command-details", classes="split-right")
            with TabPane("Wizard", id="wizard"):
                yield Static(
                    "Scegli cosa vuoi ottenere. GCC mostrera sempre i comandi prima di eseguirli.",
                    classes="hint",
                )
                with Horizontal(classes="toolbar"):
                    yield Select(
                        [(label, key) for key, label in GOALS.items()],
                        value="save",
                        allow_blank=False,
                        id="goal-select",
                    )
                    yield Input(
                        placeholder="Messaggio, nome branch o percorso file",
                        id="goal-value",
                    )
                    yield Button("Crea piano", id="build-plan", variant="primary")
                    yield Button("Esegui piano", id="execute-plan", variant="success")
                yield Markdown("Nessun piano creato.", id="plan-preview")
                yield Static("", id="operation-output")
            with TabPane("Cronologia", id="history"):
                yield Static(
                    "Grafo di tutti i branch. Hash, data, autore, riferimenti e messaggio.",
                    classes="hint",
                )
                yield RichLog(highlight=True, markup=False, wrap=False, id="history-log")
            with TabPane("Branch", id="branches"):
                with Horizontal(classes="toolbar"):
                    yield Input(placeholder="Nome branch", id="branch-name")
                    yield Button("Crea", id="create-branch", variant="primary")
                    yield Button("Checkout", id="checkout-branch")
                    yield Button("Elimina", id="delete-branch", variant="warning")
                yield DataTable(id="branch-table")
            with TabPane("Diff", id="diff"):
                with Horizontal(classes="toolbar"):
                    yield Input(placeholder="Percorso opzionale", id="diff-path")
                    yield Checkbox("Staged", id="diff-staged")
                    yield Button("Aggiorna diff", id="refresh-diff", variant="primary")
                yield RichLog(highlight=True, markup=False, wrap=False, id="diff-log")
            with TabPane("Recovery", id="recovery"):
                yield Static(
                    "Reflog locale in sola lettura. Copia un selettore e verifica "
                    "prima di recuperare.",
                    classes="hint",
                )
                yield DataTable(id="reflog-table")
            with TabPane("Impara", id="learn"):
                with Horizontal(classes="toolbar"):
                    yield Select(
                        [
                            ("Principiante", "beginner"),
                            ("Intermedio", "intermediate"),
                            ("Avanzato", "advanced"),
                            ("Esperto", "expert"),
                        ],
                        value="beginner",
                        allow_blank=False,
                        id="lesson-select",
                    )
                    yield Button("Crea sandbox", id="create-sandbox", variant="primary")
                yield Markdown(LESSONS["beginner"], id="lesson-content")
                yield Static("", id="sandbox-path")
        yield Footer()

    def on_mount(self) -> None:
        theme_names = {"dark": "textual-dark", "light": "textual-light"}
        requested_theme = theme_names.get(self.settings.theme, self.settings.theme)
        if requested_theme in self.available_themes:
            self.theme = requested_theme
        custom_actions = {
            "refresh": ("refresh_repository", "Aggiorna"),
            "quit": ("quit", "Esci"),
            "help": ("show_help", "Aiuto"),
        }
        for name, key in self.settings.shortcuts.items():
            if name in custom_actions and key:
                action, description = custom_actions[name]
                self.bind(key, action, description=description)

        command_table = self.query_one("#command-table", DataTable)
        command_table.add_columns("Comando", "Categoria", "Rischio")
        command_table.cursor_type = "row"
        branch_table = self.query_one("#branch-table", DataTable)
        branch_table.add_columns("", "Branch", "Tipo", "Tracking", "Commit")
        branch_table.cursor_type = "row"
        reflog_table = self.query_one("#reflog-table", DataTable)
        reflog_table.add_columns("Selettore", "Hash", "Azione", "Messaggio")
        reflog_table.cursor_type = "row"
        self._refresh_command_table()
        self.action_refresh_repository()
        self.set_interval(self.settings.refresh_interval, self.action_refresh_repository)

    def action_show_help(self) -> None:
        self.notify(
            "Naviga con Tab/Shift+Tab. Premi Invio sulle tabelle. "
            "R aggiorna il repository, Q esce.",
            title="Aiuto contestuale",
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
        remote_text = " | ".join(snapshot.remotes) or "nessun remote"
        self.query_one("#repo-strip", Static).update(
            f"[bold]{escape(snapshot.name)}[/bold]  {escape(str(snapshot.path))}\n"
            f"Branch: [cyan]{escape(snapshot.branch)}[/cyan]  |  "
            f"Sync: {escape(snapshot.sync_label)}  |  Remote: {escape(remote_text)}"
        )
        last_commit = "Nessun commit"
        if snapshot.last_commit_at is not None:
            last_commit = (
                f"`{snapshot.last_commit_hash}` {snapshot.last_commit_message}\n"
                f"Autore: **{snapshot.last_commit_author}** - "
                f"{self._elapsed(snapshot.last_commit_at)}"
            )
        dashboard = (
            "# Stato repository\n\n"
            f"**Percorso:** `{snapshot.path}`\n\n"
            f"**Branch attivo:** `{snapshot.branch}`  \n"
            f"**Upstream:** `{snapshot.upstream or 'non configurato'}`  \n"
            f"**Sincronizzazione:** {snapshot.sync_label}\n\n"
            "## Worktree\n\n"
            f"- File modificati: **{snapshot.modified_count}**\n"
            f"- File staged: **{snapshot.staged_count}**\n"
            f"- File non tracciati: **{snapshot.untracked_count}**\n"
            f"- Commit avanti: **{snapshot.ahead}**\n"
            f"- Commit indietro: **{snapshot.behind}**\n\n"
            f"## Ultimo commit\n\n{last_commit}\n\n"
            f"## Remote\n\n{remote_text}"
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
                "remoto" if branch.remote else "locale",
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

    @staticmethod
    def _elapsed(value: datetime) -> str:
        now = datetime.now(UTC)
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        seconds = max(0, int((now - value.astimezone(UTC)).total_seconds()))
        if seconds < 60:
            return "meno di un minuto fa"
        if seconds < 3600:
            return f"{seconds // 60} minuti fa"
        if seconds < 86_400:
            return f"{seconds // 3600} ore fa"
        return f"{seconds // 86_400} giorni fa"

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
                command.category,
                command.risk.value.upper(),
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
        errors = "\n".join(f"- {item}" for item in command.common_errors) or "- Nessuno noto"
        rollback = command.rollback or "Non necessario: il comando non modifica il repository."
        alternative = (
            f"\n\n## Alternativa consigliata\n\n{command.recommended_alternative}"
            if command.recommended_alternative
            else ""
        )
        content = f"""# {command.name}

**Sintassi:** `{command.syntax}`
**Categoria:** {command.category}
**Rischio:** **{command.risk.value.upper()}**

## Descrizione

{command.description}

**Quando usarlo:** {command.use_when}
**Quando NON usarlo:** {command.avoid_when}

**Esempio:** `{command.example}`

## Errori comuni

{errors}

## Conseguenze e rollback

{command.consequences}

**Rollback:** {rollback}{alternative}
"""
        self.query_one("#command-details", Markdown).update(content)

    @on(Button.Pressed, "#build-plan")
    def build_wizard_plan(self) -> None:
        goal = str(self.query_one("#goal-select", Select).value)
        value = self.query_one("#goal-value", Input).value
        try:
            self._set_plan(build_plan(goal, value=value))
        except ValueError as error:
            self.notify(str(error), severity="warning")

    def _set_plan(self, plan: CommandPlan) -> None:
        self.current_plan = plan
        commands = "\n".join(f"1. `{command}`" for command in plan.display_commands)
        rollback = plan.rollback or "Non necessario."
        self.query_one("#plan-preview", Markdown).update(
            f"# {plan.title}\n\n{plan.explanation}\n\n"
            f"**Rischio:** {plan.risk.value.upper()}\n\n"
            f"## Comandi\n\n{commands}\n\n**Rollback:** {rollback}"
        )

    @on(Button.Pressed, "#execute-plan")
    def execute_current_plan(self) -> None:
        if self.current_plan is None:
            self.notify("Crea prima un piano.", severity="warning")
            return
        self._request_execution(self.current_plan)

    @on(Button.Pressed, "#create-branch")
    def create_branch(self) -> None:
        name = self.query_one("#branch-name", Input).value
        try:
            plan = build_plan("branch", value=name)
        except ValueError as error:
            self.notify(str(error), severity="warning")
            return
        self._set_plan(plan)
        self._request_execution(plan)

    @on(Button.Pressed, "#checkout-branch")
    def checkout_branch(self) -> None:
        name = self.query_one("#branch-name", Input).value.strip()
        if not name:
            self.notify("Inserisci il nome del branch.", severity="warning")
            return
        plan = CommandPlan(
            title=f"Checkout {name}",
            explanation="Passa al branch esistente indicato.",
            commands=[["switch", name]],
            risk=RiskLevel.LOW,
            rollback="git switch - torna al branch precedente.",
        )
        self._request_execution(plan)

    @on(Button.Pressed, "#delete-branch")
    def delete_branch(self) -> None:
        name = self.query_one("#branch-name", Input).value
        try:
            self._request_execution(branch_delete_plan(name))
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
        if value in LESSONS:
            self.query_one("#lesson-content", Markdown).update(LESSONS[value])

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
            self.query_one("#sandbox-path", Static).update,
            f"Sandbox pronta: [bold]{escape(str(path))}[/bold]",
        )

    def _request_execution(self, plan: CommandPlan) -> None:
        if plan.risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            self.push_screen(ConfirmScreen(plan), lambda answer: self._confirmed(plan, answer))
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
            f"[bold red]Operazione bloccata[/bold red]\n{escape(message)}"
        )
        self.notify(message, severity="error")

    def _show_results(self, results: list[Any]) -> None:
        lines: list[str] = []
        succeeded = True
        for result in results:
            marker = "OK" if result.succeeded else "ERRORE"
            lines.append(f"[{marker}] {result.command}")
            if result.stdout:
                lines.append(result.stdout)
            if result.stderr:
                lines.append(result.stderr)
            succeeded = succeeded and result.succeeded
        self.query_one("#operation-output", Static).update(escape("\n".join(lines)))
        self.notify(
            "Operazione completata." if succeeded else "Il comando Git ha restituito un errore.",
            severity="information" if succeeded else "error",
        )
        self.action_refresh_repository()
