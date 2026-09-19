# Architecture

The agent is organized around two protocols. `LLMProvider.complete()` turns a transcript and tool schemas into a response. `Tool.run()` performs one bounded action and returns plain text. The `Agent` class joins these protocols with a maximum step count and persistent SQLite transcript.

```text
user task
   |
   v
SQLite transcript <-> ReAct Agent <-> OpenCode-compatible provider
                         |
              file | shell | search | GitHub
```

Each iteration stores the assistant response before dispatching calls. Each tool result is stored as a `tool` message. If the model emits no call, its text is the final answer. If the step limit is reached, the user receives an explicit incomplete-run message and the transcript path.

The file tool resolves paths and rejects anything outside the configured workspace. The shell tool runs with a timeout and rejects a small list of destructive patterns. These controls reduce accidental damage but are not a substitute for a real OS sandbox. GitHub write operations should therefore be used only with a least-privilege token and a reviewable clone.
