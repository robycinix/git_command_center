<p align="center">
  <img src="docs/assets/banner.svg" alt="Git Command Center" width="100%">
</p>

<p align="center">
  <strong>A visual, guided and safety-first Git assistant for the terminal.</strong>
</p>

<p align="center">
  <a href="https://github.com/robycinix/git_command_center/actions/workflows/ci.yml"><img src="https://github.com/robycinix/git_command_center/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/Python-3.13%2B-3776AB?logo=python&logoColor=white" alt="Python 3.13+">
  <img src="https://img.shields.io/badge/Textual-TUI-7C3AED" alt="Textual TUI">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-22C55E" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/status-alpha-F59E0B" alt="Alpha status">
</p>

Git Command Center (GCC) turns Git from a command-memory exercise into a clear,
inspectable workflow. It shows what is happening, explains what each command
will do, highlights risk, and keeps the exact Git command visible at every step.

> [!IMPORTANT]
> GCC is currently an alpha release. The local Git workflows are functional;
> hosted-provider writes, AI calls and the visual conflict editor remain planned.

## Why GCC?

Most Git tools optimize for speed after you already understand Git. GCC also
optimizes for understanding:

- **See the repository** - branch, remotes, worktree, upstream divergence and
  latest commit in one dashboard.
- **Learn while working** - every command includes syntax, use cases, failure
  modes, consequences, risk and rollback guidance.
- **Ask for an outcome** - choose "save my work", "download updates" or
  "create a branch" and inspect the generated plan.
- **Keep control** - commands are passed as argument lists, never evaluated as
  arbitrary shell input.
- **Practice safely** - create disposable local repositories for exercises and
  experiments.

## Highlights

| Area | What it provides |
| --- | --- |
| Dashboard | Repository path, remotes, branch, sync state, file counts and latest commit |
| Command explorer | Live search, category filters, risk filters and educational reference |
| Guided wizard | Intent-based plans with exact commands and rollback guidance |
| History | Decorated, readable commit graph across branches and tags |
| Branches | Local/remote visibility, tracking state, create, switch and guarded delete |
| Diff & recovery | Unified diff viewer plus a chronological reflog timeline |
| Learning | Beginner-to-expert lessons, quizzes, exercises and disposable sandboxes |
| Safety | Risk classification, explicit confirmation and typed confirmation for critical actions |

<p align="center">
  <img src="docs/assets/dashboard.svg" alt="Git Command Center dashboard" width="94%">
</p>

## Quick Start

Python 3.13 or newer is required.

```bash
python -m pip install -e .
gcc-tui
```

Open a specific repository:

```bash
gcc-tui /path/to/repository
```

Install in an isolated environment with `pipx`:

```bash
pipx install git-command-center
git-command-center /path/to/repository
```

## Safety Model

Every executable operation is represented by a typed `CommandPlan`. GCC shows
the exact commands before execution and applies these invariants:

1. shell operators and control characters are rejected;
2. subprocesses run with argument lists and `shell=False`;
3. high-risk actions require explicit confirmation;
4. critical actions additionally require typing `CONFERMO`;
5. a multi-command plan stops after its first failure;
6. AI and GitHub provider boundaries perform no network activity by default.

## Architecture

```mermaid
flowchart LR
    User["User intent"] --> UI["Textual UI"]
    UI --> Planner["Command planner"]
    Planner --> Policy["Safety policy"]
    Policy --> Git["Git service"]
    Git --> Repo["Local repository"]
    Repo --> UI
```

The codebase separates domain models, repository access, application services,
provider interfaces, configuration and presentation. Repository reads and Git
operations run in Textual workers so the interface remains responsive.

Read the full [architecture](docs/architecture.md) and
[roadmap](docs/roadmap.md).

## Development

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m mypy src
python -m pytest
```

Build a wheel and a native executable for the current operating system:

```bash
python -m pip wheel . --no-deps --wheel-dir dist
python -m PyInstaller --clean --noconfirm git-command-center.spec
```

PyInstaller is not a cross-compiler. Windows, Linux and macOS executables must
be built on their respective operating systems.

## Configuration

GCC creates a validated YAML configuration file on first run under the platform
configuration directory. Available themes include Dark, Light, Dracula, Nord
and Gruvbox; refresh, quit and help shortcuts can be customized.

## Contributing

Contributions that improve clarity, safety or teaching value are welcome. Read
[CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Security issues
should follow [SECURITY.md](SECURITY.md).

## License

Released under the [MIT License](LICENSE).
