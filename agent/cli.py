from __future__ import annotations

import argparse
import logging
import os

from .core import Agent
from .github import GitHubTool
from .memory import Memory
from .opencode import OpenCodeProvider
from .tools import FileTool, ShellTool, WebSearchTool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lightweight terminal AI coding agent")
    parser.add_argument("task", nargs="?", help="Task for the agent")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--memory", default="~/.autonomous-coder/memory.sqlite3")
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--allow-network", action="store_true", help="Allow shell curl/wget; dedicated search and GitHub tools work without this")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.task:
        print("Provide a task, for example: autocoder 'Fix issue #12 in owner/repo'")
        return 2
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)
    tools = [FileTool(args.workspace), ShellTool(args.workspace, allow_network=args.allow_network), WebSearchTool(), GitHubTool(workspace=args.workspace)]
    agent = Agent(OpenCodeProvider(base_url=args.base_url, model=args.model), tools, Memory(args.memory), args.max_steps)
    print(agent.run(args.task))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
