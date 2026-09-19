# Autonomous Coder

Autonomous Coder is a lightweight, terminal-based AI coding agent written in Python using only the standard library at runtime. It uses a bounded **ReAct loop**: the model proposes a tool action, the agent executes it, records the result in SQLite, and sends the result back to the model. The design supports Linux, macOS, and Android through Termux.

> **Safety note:** This project is an extensible coding assistant, not an unattended security boundary. Run it in a disposable clone, review generated diffs, and use a GitHub token with the smallest practical permissions. Pull requests are not opened by the offline demo.

## Features

- OpenCode-compatible, OpenAI-style `/v1/chat/completions` provider.
- Persistent session memory in a local SQLite database.
- Workspace-confined file reads and writes.
- Shell execution with timeouts and a small destructive-command denylist.
- SearxNG-compatible web search for public documentation.
- GitHub REST operations for issue reading and pull-request creation, plus local branch and commit helpers.
- No mandatory third-party Python packages. The standard library is sufficient.
- Deterministic offline simulation and unit tests.

## Project structure

```text
agent/
  core.py       bounded ReAct orchestration and memory integration
  github.py     GitHub REST client and git automation tool
  memory.py     SQLite transcript persistence
  opencode.py   OpenCode/OpenAI-compatible provider
  tools.py      file, shell, and SearxNG tools
  types.py      shared dataclasses and protocols
  cli.py        terminal entry point
examples/
  simulated_run.py  offline end-to-end demonstration
 tests/
  test_agent.py     standard-library unit tests
requirements.txt     intentionally empty runtime dependency file
```

## Linux or macOS setup

Install Python 3.10 or newer, then clone or copy this directory:

```bash
cd autonomous-coder
python3 -m venv .venv
. .venv/bin/activate
python3 -m unittest discover -s tests -v
PYTHONPATH=. python3 examples/simulated_run.py
```

The simulation does not contact OpenCode or GitHub. It verifies that the agent can call a search tool, write a file, run a test command, and retain a transcript.

## Termux setup

```bash
pkg update
pkg install python git
cd ~/autonomous-coder
python -m unittest discover -s tests -v
```

Termux uses the same command-line interface. No compiler, Docker daemon, or native Python extension is required.

## Configure OpenCode

The adapter accepts an OpenCode server or any OpenAI-compatible gateway:

```bash
export OPENCODE_BASE_URL="http://127.0.0.1:4096/v1"
export OPENCODE_MODEL="opencode/big-pickle"
# Set this only when the gateway requires authentication.
export OPENCODE_API_KEY="..."
```

Run a task from the repository root:

```bash
PYTHONPATH=. python3 -m agent.cli \
  --workspace . \
  "Inspect the repository, fix the failing tests, and explain the changes."
```

Useful options include `--max-steps 8`, `--memory ~/.autonomous-coder/memory.sqlite3`, and `--verbose`. A new SQLite session is created for each invocation; the stored transcript can be searched or reused by extending the CLI later.

## Configure web search

The default endpoint is a public SearxNG-compatible JSON endpoint. For a private instance, set:

```bash
export SEARXNG_URL="https://your-searxng.example/search"
```

The agent exposes search as a dedicated tool instead of encouraging arbitrary `curl` calls from the shell.

## Configure GitHub

Create a fine-grained GitHub token with access only to the repositories that the agent needs. Then set:

```bash
export GITHUB_TOKEN="..."
```

The GitHub tool supports these actions:

- `issue`: read an issue through `GET /repos/{owner}/{repo}/issues/{number}`.
- `branch`: create a local branch.
- `commit`: stage and commit local changes.
- `push`: push the named branch to `origin` with upstream tracking.
- `pull_request`: call `POST /repos/{owner}/{repo}/pulls`.

A model can invoke the tool during a run, but the operator should still review the diff and test output before allowing a production repository workflow. The local git helper does not force-push.

## ReAct contract

The provider receives the conversation plus JSON tool schemas. If it returns `tool_calls`, the agent dispatches each call and appends a `tool` message containing the exact result. The loop stops on a model response without tool calls or after `--max-steps`. This bound prevents accidental infinite loops and preserves a complete audit trail in SQLite.

New tools can be added by implementing `name`, `description`, `schema()`, and `run(arguments)`, then passing the instance to `Agent`. New LLM providers only need to implement `complete(messages, tools)` and return `LLMResponse`.

## Limitations and extension points

The current implementation deliberately avoids automatic force-pushes, secrets management, sandbox virtualization, and broad filesystem access. Production deployments should add OS-level sandboxing, explicit approval gates for branch and pull-request actions, structured patch validation, rate-limit handling, and stronger command policy enforcement. These concerns are isolated behind the tool interfaces so they can be added without rewriting the loop.

## License

MIT. See `LICENSE`.
