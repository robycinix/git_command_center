from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GitHubStatus:
    available: bool
    message: str


class GitHubService:
    """Boundary for a future GitHub API adapter.

    This release deliberately exposes no write operation and never asks for a token.
    """

    def status(self) -> GitHubStatus:
        return GitHubStatus(
            available=False,
            message="GitHub API integration is not configured; local Git remains fully available.",
        )
