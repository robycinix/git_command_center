from __future__ import annotations

import argparse
from pathlib import Path

from git_command_center.config.settings import load_settings
from git_command_center.git.service import GitService, RepositoryError
from git_command_center.i18n import SUPPORTED_LANGUAGES, Translator
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
    parser.add_argument(
        "--language",
        "-L",
        choices=("auto", *SUPPORTED_LANGUAGES),
        help="Temporary interface language override (default: saved preference).",
    )
    return parser


def main() -> None:
    arguments = build_parser().parse_args()
    try:
        service = GitService(arguments.repository)
        settings = load_settings()
        translator = Translator(arguments.language or settings.language)
    except (RepositoryError, ValueError) as error:
        raise SystemExit(f"Git Command Center: {error}") from error
    GCCApp(service, settings, translator).run()


if __name__ == "__main__":
    main()
