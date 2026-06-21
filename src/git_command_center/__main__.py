from __future__ import annotations

import argparse
from pathlib import Path

from git_command_center.config.settings import load_settings
from git_command_center.git.service import GitService, RepositoryError
from git_command_center.ui.app import GCCApp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gcc-tui",
        description="Launch the safe and educational Git Command Center TUI.",
    )
    parser.add_argument(
        "repository",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="Repository path (defaults to the current directory).",
    )
    return parser


def main() -> None:
    arguments = build_parser().parse_args()
    try:
        service = GitService(arguments.repository)
        settings = load_settings()
    except (RepositoryError, ValueError) as error:
        raise SystemExit(f"Git Command Center: {error}") from error
    GCCApp(service, settings).run()


if __name__ == "__main__":
    main()
