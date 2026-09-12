"""Provider interface for the AI coach, so a different provider (e.g.
Claude) can be swapped in later without touching anything that calls it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class CoachError(Exception):
    """Base class for coach failures. Callers should show a friendly
    message rather than a raw traceback.
    """


class CoachConnectionError(CoachError):
    """No internet, DNS failure, timeout, or similar - the provider
    couldn't be reached at all.
    """


class CoachRateLimitError(CoachError):
    """The provider's API rate limit was hit."""


class CoachProvider(ABC):
    @abstractmethod
    def generate_review(self, context: str, system_prompt: str) -> str:
        """Return the coach's review/advice text for the given context."""
