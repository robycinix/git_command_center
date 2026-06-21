"""Optional, provider-neutral AI integration points."""

from git_command_center.ai.provider import AIProvider, DisabledAIProvider

__all__ = ["AIProvider", "DisabledAIProvider"]
