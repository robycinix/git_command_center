from __future__ import annotations

import argparse
from pathlib import Path

from git_command_center.config.settings import load_settings
from git_command_center.git.service import GitService, RepositoryError
from git_command_center.i18n import SUPPORTED_LANGUAGES, Translator
from git_command_center.services.path_setup import (
    PathSetupError,
    PathSetupStatus,
    setup_user_path,
)
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
    parser.add_argument(
        "--setup-path",
        action="store_true",
        help="Add the gcc-tui launcher directory to the user PATH and exit.",
    )
    return parser


def main() -> None:
    arguments = build_parser().parse_args()
    try:
        settings = load_settings()
        translator = Translator(arguments.language or settings.language)
    except ValueError as error:
        raise SystemExit(f"Git Command Center: {error}") from error

    if arguments.setup_path:
        try:
            result = setup_user_path()
        except PathSetupError as error:
            raise SystemExit(translator("path_setup.missing")) from error
        message_key = (
            "path_setup.already"
            if result.status is PathSetupStatus.ALREADY_PRESENT
            else "path_setup.added"
        )
        print(translator(message_key, path=result.scripts_directory))
        if result.status is PathSetupStatus.ADDED:
            print(translator("path_setup.reopen"))
        return

    try:
        service = GitService(arguments.repository)
    except RepositoryError as error:
        raise SystemExit(f"Git Command Center: {error}") from error
    GCCApp(service, settings, translator).run()


if __name__ == "__main__":
    main()
