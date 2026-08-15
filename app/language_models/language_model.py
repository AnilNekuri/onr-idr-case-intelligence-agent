"""Storage- and provider-independent language-model contract."""

from typing import Protocol


class LanguageModelError(RuntimeError):
    """Raised when a language-model request or response fails."""


class LanguageModel(Protocol):
    """Narrow text-generation interface used by application orchestration."""

    def generate(self, prompt: str) -> str:
        """Generate text from one complete prompt."""
        ...
