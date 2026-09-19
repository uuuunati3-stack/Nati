from __future__ import annotations

import json
import logging
from typing import Any

from .memory import Memory
from .types import LLMProvider, Message, Tool

LOG = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an autonomous coding agent. Work in small, verifiable steps.
Use file and shell tools to inspect, modify, and test the repository. Use web_search for current documentation.
Use github issue to obtain requirements. Before any pull request, ensure tests pass and explain the diff.
Never claim a tool action succeeded unless its tool result says so. Stop when the requested work is complete.
"""


class Agent:
    def __init__(self, provider: LLMProvider, tools: list[Tool], memory: Memory | None = None, max_steps: int = 12):
        self.provider = provider
        self.tools = {tool.name: tool for tool in tools}
        self.memory = memory or Memory()
        self.max_steps = max_steps

    def run(self, task: str, session_id: int | None = None) -> str:
        session_id = session_id or self.memory.new_session()
        messages = self.memory.load(session_id)
        if not messages or messages[0].role != "system":
            messages.insert(0, Message("system", SYSTEM_PROMPT))
            self.memory.append(session_id, messages[0])
        user = Message("user", task)
        messages.append(user)
        self.memory.append(session_id, user)
        schemas = [tool.schema() for tool in self.tools.values()]
        for step in range(1, self.max_steps + 1):
            response = self.provider.complete(messages, schemas)
            assistant = Message("assistant", response.content)
            messages.append(assistant)
            self.memory.append(session_id, assistant)
            if not response.tool_calls:
                return response.content
            for call in response.tool_calls:
                tool = self.tools.get(call.name)
                result = f"ERROR: unknown tool {call.name}" if tool is None else tool.run(call.arguments)
                LOG.info("step=%s tool=%s result=%s", step, call.name, result[:300].replace("\n", " "))
                tool_message = Message("tool", result, name=call.name, tool_call_id=call.call_id)
                messages.append(tool_message)
                self.memory.append(session_id, tool_message)
        return f"Stopped after {self.max_steps} steps without a final answer. Review the transcript in {self.memory.path}."
