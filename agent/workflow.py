from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from .core import Agent
from .github import GitHubClient
from .memory import Memory
from .opencode import OpenCodeProvider
from .tools import FileTool, ShellTool, WebSearchTool


def run(command: str, cwd: str) -> str:
    result = subprocess.run(command, cwd=cwd, shell=True, text=True, capture_output=True, timeout=180)
    output = (result.stdout + result.stderr).strip()
    if result.returncode:
        raise RuntimeError(f"{command} failed ({result.returncode}): {output[-4000:]}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the issue-to-PR OpenCode workflow")
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""), help="owner/name")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--base", default="main")
    args = parser.parse_args()
    if not args.repo or "/" not in args.repo:
        raise SystemExit("--repo or GITHUB_REPOSITORY must be owner/name")

    client = GitHubClient()
    issue = client.issue(args.repo, args.issue)
    title = issue.get("title", f"Issue #{args.issue}")
    body = issue.get("body") or "(no issue body)"
    branch = f"autocoder/issue-{args.issue}"
    workspace = str(Path(args.workspace).resolve())
    memory = Memory(os.getenv("AUTOCODER_MEMORY", "~/.autonomous-coder/actions.sqlite3"))
    tools = [FileTool(workspace), ShellTool(workspace), WebSearchTool()]
    task = f"""Solve this GitHub issue in the repository. Inspect the existing code first, make the smallest correct change, run the relevant tests, and summarize the change. Do not modify generated files or secrets.\n\nIssue #{args.issue}: {title}\n{body}"""
    result = Agent(OpenCodeProvider(), tools, memory, max_steps=int(os.getenv("AUTOCODER_MAX_STEPS", "16"))).run(task)
    print(result)

    diff = run("git diff --stat && git diff --check", workspace)
    if not diff.strip():
        raise SystemExit("Agent produced no working-tree changes; refusing to create a pull request")
    run("git switch -c " + branch, workspace)
    run("git add -A && git commit -m " + shell_quote(f"Fix issue #{args.issue}: {title}"), workspace)
    run("git push --set-upstream origin " + branch, workspace)
    pr = client.pull_request(args.repo, f"Fix #{args.issue}: {title}", f"Closes #{args.issue}\n\nOpenCode agent summary:\n{result}\n\nDiff check:\n{diff}", branch, args.base)
    print(f"Pull request created: {pr.get('html_url', pr)}")
    return 0


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


if __name__ == "__main__":
    raise SystemExit(main())
