"""Storage- and provider-independent language-model contracts."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


class LanguageModelError(RuntimeError):
    """Raised when a language-model request or response fails."""


class LanguageModel(Protocol):
    """Narrow text-generation interface used by application orchestration."""

    def generate(self, prompt: str) -> str:
        """Generate text from one complete prompt."""
        ...


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """One application function made available to a language model."""

    name: str
    description: str
    parameters: dict[str, object]


@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    """Inspectable record of one model-requested application tool call."""

    name: str
    arguments: dict[str, object]
    output: str


@dataclass(frozen=True, slots=True)
class ToolCallingResult:
    """Final model text and the tool calls used to produce it."""

    text: str
    tool_calls: tuple[ToolCallRecord, ...]


ToolExecutor = Callable[[str, dict[str, object]], str]


class ToolCallingLanguageModel(LanguageModel, Protocol):
    """A model that can choose and invoke application-defined functions."""

    def generate_with_tools(
        self,
        prompt: str,
        tools: tuple[ToolDefinition, ...],
        execute_tool: ToolExecutor,
        *,
        max_rounds: int = 5,
    ) -> ToolCallingResult:
        """Run model/tool turns until the model returns final text."""
        ...
