from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


class ShellTool:
    name = "shell"
    description = "Run a shell command in the workspace. Destructive commands and commands outside the workspace are blocked."

    def __init__(self, workspace: str = ".", timeout: int = 120, allow_network: bool = False):
        self.workspace = Path(workspace).resolve()
        self.timeout = timeout
        self.allow_network = allow_network
        self.blocked = ("rm -rf /", "mkfs", ":(){", "shutdown", "reboot", "dd if=", "git push --force")

    def schema(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}

    def run(self, arguments: dict[str, Any]) -> str:
        command = str(arguments.get("command", "")).strip()
        if not command:
            return "ERROR: command is required"
        if any(token in command.lower() for token in self.blocked):
            return "ERROR: blocked potentially destructive command"
        if not self.allow_network and any(x in command.split()[:1] for x in ("curl", "wget", "nc")):
            return "ERROR: network command blocked; use the web_search or github tool"
        try:
            result = subprocess.run(command, cwd=self.workspace, shell=True, text=True, capture_output=True, timeout=self.timeout)
            output = (result.stdout + result.stderr).strip()
            return f"exit_code={result.returncode}\n{output[-12000:]}"
        except subprocess.TimeoutExpired:
            return f"ERROR: command timed out after {self.timeout}s"


class FileTool:
    name = "file"
    description = "Read or write UTF-8 text files within the workspace."

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace).resolve()

    def schema(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["read", "write"]}, "path": {"type": "string"}, "content": {"type": "string"}}, "required": ["action", "path"]}}

    def _safe(self, path: str) -> Path:
        candidate = (self.workspace / path).resolve()
        if candidate != self.workspace and self.workspace not in candidate.parents:
            raise ValueError("path escapes workspace")
        return candidate

    def run(self, arguments: dict[str, Any]) -> str:
        try:
            path = self._safe(str(arguments.get("path", "")))
            if arguments.get("action") == "read":
                return path.read_text(encoding="utf-8")[-20000:]
            if arguments.get("action") == "write":
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(str(arguments.get("content", "")), encoding="utf-8")
                return f"wrote {path.relative_to(self.workspace)}"
            return "ERROR: action must be read or write"
        except (OSError, ValueError) as exc:
            return f"ERROR: {exc}"


class WebSearchTool:
    name = "web_search"
    description = "Search public documentation using a SearxNG-compatible JSON endpoint."

    def __init__(self, endpoint: str | None = None):
        self.endpoint = endpoint or os.getenv("SEARXNG_URL", "https://search.linuxserver.io/search")

    def schema(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}

    def run(self, arguments: dict[str, Any]) -> str:
        import urllib.parse, urllib.request
        query = str(arguments.get("query", "")).strip()
        url = self.endpoint + "?" + urllib.parse.urlencode({"q": query, "format": "json", "language": "en"})
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                data = json.loads(response.read().decode())
            return "\n".join(f"{i+1}. {r.get('title')}\n{r.get('url')}\n{r.get('content','')}" for i, r in enumerate(data.get("results", [])[:5])) or "No results"
        except Exception as exc:
            return f"ERROR: search failed: {exc}"
