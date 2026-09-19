from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from .types import LLMResponse, Message, ToolCall


class OpenCodeProvider:
    """OpenAI-compatible adapter for OpenCode or any compatible local gateway."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None, timeout: int = 120):
        self.base_url = (base_url or os.getenv("OPENCODE_BASE_URL", "http://127.0.0.1:4096/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("OPENCODE_API_KEY", "")
        self.model = model or os.getenv("OPENCODE_MODEL", "opencode/big-pickle")
        self.timeout = timeout

    def complete(self, messages: list[Message], tools: list[dict[str, Any]]) -> LLMResponse:
        payload: dict[str, Any] = {"model": self.model, "messages": [m.__dict__ for m in messages], "temperature": 0.1}
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]
            payload["tool_choice"] = "auto"
        request = urllib.request.Request(self.base_url + "/chat/completions", data=json.dumps(payload).encode(), method="POST")
        request.add_header("Content-Type", "application/json")
        if self.api_key:
            request.add_header("Authorization", f"Bearer {self.api_key}")
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            raw = json.loads(response.read().decode())
        choice = raw["choices"][0]["message"]
        calls = []
        for call in choice.get("tool_calls", []):
            fn = call.get("function", {})
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            calls.append(ToolCall(name=fn.get("name", ""), arguments=args, call_id=call.get("id", "")))
        return LLMResponse(content=choice.get("content") or "", tool_calls=calls, raw=raw)
