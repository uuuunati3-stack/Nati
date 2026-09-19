from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from .tools import ShellTool


class GitHubClient:
    def __init__(self, token: str | None = None, api_url: str | None = None):
        self.token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN", "")
        self.api_url = (api_url or os.getenv("GITHUB_API_URL", "https://api.github.com")).rstrip("/")

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = urllib.request.Request(self.api_url + path, method=method, data=json.dumps(payload).encode() if payload else None)
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("User-Agent", "autonomous-coder")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        if payload:
            request.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())

    def issue(self, repo: str, number: int) -> dict[str, Any]:
        return self.request("GET", f"/repos/{repo}/issues/{number}")

    def pull_request(self, repo: str, title: str, body: str, head: str, base: str = "main") -> dict[str, Any]:
        return self.request("POST", f"/repos/{repo}/pulls", {"title": title, "body": body, "head": head, "base": base})


class GitHubTool:
    name = "github"
    description = "Read a GitHub issue, create a branch, commit and push changes, or open a pull request."

    def __init__(self, client: GitHubClient | None = None, workspace: str = "."):
        self.client = client or GitHubClient()
        self.git = ShellTool(workspace=workspace, allow_network=True)

    def schema(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["issue", "branch", "commit", "push", "pull_request"]}, "repo": {"type": "string"}, "number": {"type": "integer"}, "name": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}, "head": {"type": "string"}, "base": {"type": "string"}}, "required": ["action"]}}

    def run(self, arguments: dict[str, Any]) -> str:
        action = arguments.get("action")
        try:
            if action == "issue":
                return json.dumps(self.client.issue(arguments["repo"], int(arguments["number"])), indent=2)
            if action == "branch":
                return self.git.run({"command": f"git switch -c {self._git_name(arguments['name'])}"})
            if action == "commit":
                return self.git.run({"command": f"git add -A && git commit -m {self._quote(arguments.get('name', 'AI change'))}"})
            if action == "push":
                branch = self._git_name(arguments.get("name", ""))
                return self.git.run({"command": f"git push -u origin {branch}"})
            if action == "pull_request":
                return json.dumps(self.client.pull_request(arguments["repo"], arguments["title"], arguments.get("body", ""), arguments["head"], arguments.get("base", "main")), indent=2)
            return "ERROR: unsupported GitHub action"
        except Exception as exc:
            return f"ERROR: GitHub operation failed: {exc}"

    @staticmethod
    def _git_name(value: str) -> str:
        return "".join(c for c in str(value) if c.isalnum() or c in "-_/")[:80] or "ai-change"

    @staticmethod
    def _quote(value: str) -> str:
        return "'" + str(value).replace("'", "'\\''") + "'"
