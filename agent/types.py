from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None = None
    tool_call_id: str | None = None


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str = ""


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    def complete(self, messages: list[Message], tools: list[dict[str, Any]]) -> LLMResponse: ...


class Tool(Protocol):
    name: str
    description: str

    def schema(self) -> dict[str, Any]: ...
    def run(self, arguments: dict[str, Any]) -> str: ...
