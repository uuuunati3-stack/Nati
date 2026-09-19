from __future__ import annotations

import json
import tempfile
from pathlib import Path

from agent.core import Agent
from agent.memory import Memory
from agent.types import LLMResponse, ToolCall
from agent.tools import FileTool, ShellTool, WebSearchTool


class FakeGitHubTool:
    name = "github"
    description = "Offline GitHub simulator for the demonstration."

    def schema(self):
        return {"name": self.name, "description": self.description, "parameters": {"type": "object", "properties": {"action": {"type": "string"}}}}

    def run(self, arguments):
        action = arguments.get("action")
        if action == "issue":
            return json.dumps({"number": 1, "title": "Greeting helper", "body": "Add a greeting helper", "state": "open"})
        if action in {"branch", "commit", "pull_request"}:
            return f"simulated GitHub success: {action}"
        return "ERROR: unsupported simulated action"


class DemoOpenCodeProvider:
    """Deterministic stand-in for OpenCode, used to test orchestration offline."""
    def __init__(self):
        self.step = 0

    def complete(self, messages, tools):
        self.step += 1
        calls = {
            1: [ToolCall("github", {"action": "issue", "repo": "demo/example", "number": 1})],
            2: [ToolCall("web_search", {"query": "Python pathlib write_text encoding documentation"})],
            3: [ToolCall("file", {"action": "write", "path": "hello.py", "content": "def greeting(name):\n    return f'Hello, {name}!'\n"})],
            4: [ToolCall("shell", {"command": "python3 -c \"from hello import greeting; assert greeting('Ada') == 'Hello, Ada!'\""})],
            5: [ToolCall("github", {"action": "branch", "name": "fix/greeting-helper"}), ToolCall("github", {"action": "commit", "name": "Add greeting helper"})],
            6: [ToolCall("github", {"action": "pull_request", "repo": "demo/example", "title": "Add greeting helper", "head": "fix/greeting-helper", "body": "Closes #1"})],
        }.get(self.step)
        if calls:
            return LLMResponse(f"Step {self.step}: executing planned action.", calls)
        return LLMResponse("Simulation complete: issue read, documentation searched, code written, test passed, branch and commit prepared, and PR opened in the simulator.")


def main():
    with tempfile.TemporaryDirectory() as directory:
        memory = Memory(str(Path(directory) / "memory.sqlite3"))
        tools = [FileTool(directory), ShellTool(directory), WebSearchTool(endpoint="http://127.0.0.1:1"), FakeGitHubTool()]
        agent = Agent(DemoOpenCodeProvider(), tools, memory, max_steps=8)
        print(agent.run("Read issue #1, find a bug fix, implement it, test it, and open a PR."))
        print(f"Transcript stored at: {memory.path}")


if __name__ == "__main__":
    main()
