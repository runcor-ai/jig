# Execution and safety

| Requirement (spec §9) | How v0.1 meets it |
|---|---|
| No `eval` / unrestricted execution | `lattice/parser.py` uses `ast.parse` as a grammar only, with a whitelist of nodes (calls to registered commands; literal arguments; references to earlier bindings). Nothing is ever executed. |
| Explicit parameter schemas | Every parameter in `commands.yaml` has a type, a default and an optional enum. Unknown parameters, wrong types and paths outside the project are rejected (`E_PARAM`). |
| Untrusted content | Targets, briefs, source files and earlier outputs are wrapped in `<data>` tags. The system prompt says data is never instructions, and `</data>` is escaped inside file content. This is a mitigation, not a guarantee, so the real controls are the next two rows. |
| Permissions via tool boundaries | Each command declares a tool policy (`lattice.yaml`). The adapter passes `--tools` (which tools exist at all), `--allowedTools` and `--disallowedTools`, `--permission-mode dontAsk` (anything not pre-approved is denied with no prompt), `--setting-sources project` (the user's personal allow-lists are not inherited) and `--strict-mcp-config` (no MCP servers). Analysis commands (`requirement`, `design`) get **no tools** and run in an empty sandbox dir. `review`/`verify` get Read/Grep/Glob in the workspace. `build` gets file tools scoped to the workspace and Bash limited to docker/npm/node/curl-localhost. |
| Approval for production / destructive actions | `deploy` and `rollback` have `approval_required: true`, and any command accepts `approval_required=True`. Approvals are granted only via `lattice approve <ID> <command>` at an interactive TTY, by typing the artifact id. They are single-use and recorded in `.lattice/approvals.json`. Scripts and agents cannot approve: `approve()` refuses without a TTY, and `lattice` is not in the build Bash allow-list. |
| Recording | `.lattice/runs/<run_id>/` holds the invocation, rendered prompts, the full agent event stream (`agent-events-*.jsonl`), test logs and the result. `.lattice/log.jsonl` has one line per execution. Stage outputs are append-only. |
| Safe retries | Retries happen only for commands marked `idempotent: true`, re-prompting with the validation findings. `build`, `implement` etc. are not retried automatically. |
| Observable status | `.lattice/runs/<id>/status.json` is updated with each agent tool call. `lattice status` lists running commands. |
| Explicit unavailability | Missing `claude` CLI → `E_AGENT_UNAVAILABLE`; docker down → `test` returns `E_UNAVAILABLE`; `deploy` → `E_UNAVAILABLE`. |

## Verified boundary behaviour (live, Claude Code 2.1.325)

Observed with the `build` policy:

- `Write` outside the working directory: **denied**.
- `ls ..`: **denied**.
- `python -c "open('x.txt','w')..."`, `git init`, `docker push`: **denied**.
- `npm --version`, `docker ps`: allowed.
- `whoami`: **allowed**, even though it is not in the allow-list. Claude Code auto-permits commands it
  classifies as read-only.

## Known gaps

- `docker` is allowed for `build`, and a container can do anything Docker allows (including bind-mounting
  host paths). For untrusted tasks, run Lattice inside a VM or a devcontainer.
- Read-only built-in commands are allowed by Claude Code's own classifier, beyond Lattice's allow-list.
- Prompt injection inside a workspace file could still influence a `build` agent within its tool boundary.
