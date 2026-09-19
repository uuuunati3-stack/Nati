import tempfile
import unittest
from pathlib import Path

from agent.core import Agent
from agent.memory import Memory
from agent.tools import FileTool, ShellTool
from agent.types import LLMResponse, ToolCall


class Provider:
    def __init__(self): self.calls = 0
    def complete(self, messages, tools):
        self.calls += 1
        if self.calls == 1:
            return LLMResponse("using tool", [ToolCall("file", {"action": "write", "path": "x.txt", "content": "ok"})])
        return LLMResponse("done")


class AgentTests(unittest.TestCase):
    def test_react_and_memory(self):
        with tempfile.TemporaryDirectory() as d:
            memory = Memory(str(Path(d) / "memory.sqlite3"))
            result = Agent(Provider(), [FileTool(d)], memory).run("write x")
            self.assertEqual(result, "done")
            self.assertTrue((Path(d) / "x.txt").exists())
            self.assertGreaterEqual(len(memory.search("done")), 1)

    def test_file_escape_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            result = FileTool(d).run({"action": "write", "path": "../escape.txt", "content": "bad"})
            self.assertTrue(result.startswith("ERROR:"))

    def test_shell_danger_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            result = ShellTool(d).run({"command": "rm -rf /"})
            self.assertIn("blocked", result)


if __name__ == "__main__":
    unittest.main()
