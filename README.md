# Lattice v0.2

Lattice is a small scripting language for LLM agents. You write short scripts. Each command becomes a
tool-restricted agent call (Claude Code today), its output is checked against a JSON schema plus
deterministic checks, failures are retried with feedback, and everything is recorded under `.lattice/`.

```python
spec = specify("A simple Pong game: two paddles, a ball, score to 10, player vs computer",
               constraints=["React + TypeScript + Vite, no backend"], id="PONG-001")
build(spec)
test(spec, run=["npm install", "npx vitest run --reporter=junit --outputFile=test-results/junit.xml"])
verify(spec)
```

Commands are plugins. The five built-ins use exactly the format you use to add your own.

## Quick start

Requirements: Python 3.11+ with `pyyaml` and `jsonschema`, and the `claude` CLI logged in. You also need
Node.js for the example apps, and Docker for `--sandbox docker`.

```bash
py -m pytest -q                                  # 85 offline tests, no model calls
py -m lattice check                              # command definitions, agent, sandbox
py -m lattice commands                           # loaded commands and where they came from
py -m lattice run examples/pong.lat --replace    # build Pong (about 5 min)
py -m lattice exec 'research("passkey adoption", question="How widespread in 2026?")'
py -m lattice batch examples/batches/research.yaml --script examples/pipelines/research.lat --parallel 3
```

## Script language

- **Statements:** `command(target, name=value, ...)` or `name = command(...)`.
- **Arguments:** literals (strings, numbers, booleans, `None`/`null`, lists, dicts) or variable references.
- **Bound variables:** `spec = specify(...)` keeps the whole result.
  - Passing `spec` as a value means its artifact id: `build(spec)`.
  - Dotted lookups read its data: `spec.id`, `spec.status`, `spec.output.summary`, `spec.output.requirements`.
- **Batch variables:** batch rows supply variables, e.g. `research(topic, question=question)`.
- **Never executed.** `ast.parse` is used only as a grammar, with a node whitelist. Imports, loops, operators,
  subscripts, f-strings, method calls, nested calls and names starting with `_` are all rejected.
- **Literal ids work too.** `specify("x")` followed by `build("TOY-001")` makes `specify` create exactly
  `TOY-001`.
- **Re-running.** Re-creating an existing id is refused. `--replace` archives the old artifact first, and
  `--resume` skips steps that already completed with the same inputs.

## Commands

| Command | Kind | What it does |
|---|---|---|
| `specify(goal, constraints=[], brief=None, id=None)` | agent, no tools | Goal → requirements (R-01…), decisions, components, test plan. Every constraint must be restated. |
| `build(spec, notes=None, test_run=[...])` | agent, build tools | Implements the spec in `apps/<ID>/` and makes `test_run` pass |
| `test(spec, run=[...], reports=[...], expect_files=[])` | runs in Lattice, no agent | Runs your commands and parses the real JUnit XML. No reports means fail. |
| `verify(spec)` | agent, read-only | Per-requirement status with file/symbol evidence and test citations, all checked. The verdict is computed by Lattice. |
| `research(topic, question=None, min_sources=3)` | agent, web only | Sourced findings. Every cited URL must appear in the session's own searches or fetches. |
| `review(spec, criteria=[...])` | **project command** (`commands/review.*`) | An example of a user-defined command |

### Add your own command

Put a `<name>.yaml`, a `<name>.md` (prompt template) and a `<name>.schema.json` (output schema, or inline it
in the yaml) in one of these places:

- `./commands/`: this project
- `~/.lattice/commands/`: all your projects (or `$LATTICE_USER_COMMANDS`)

Later locations override earlier ones (built-in → user → project).

```yaml
# commands/summarize.yaml
purpose: Summarize a document for a given audience.
target: {type: text, required: true}
parameters:
  source:   {type: path, default: null}        # inserted into the prompt as fenced, untrusted data
  audience: {type: string, default: executives}
tool_policy: none                              # or read_workspace / write_workspace / research / build / inline {...}
output_schema: {type: object, required: [summary], properties: {summary: {type: string}}}
validators: []
```

```markdown
<!-- commands/summarize.md -->
Summarize for $audience:
<data name="source">$source</data>
```

- **Placeholders:** `$target`, `$artifact_id`, every parameter by name, `$spec`, `$tests`, `$context` (all
  stages) and `$workspace_state`.
- **Checks:** `validators:` and `postprocess:` take names of built-in checks. `lattice check` lists unknown
  names and other definition errors, with the file and reason.

## Running many at once

```bash
lattice batch examples/batches/apps.yaml --script examples/pipelines/app.lat --parallel 3
lattice batch examples/batches/apps.yaml --script examples/pipelines/app.lat --resume
lattice batch-status apps
```

- Each item runs in its own process and its own workspace, with its own ports.
- Shared files are locked, and IDs are claimed atomically.
- `--resume` skips items that completed and resumes the rest step by step.

## Safety

- **Tool boundaries are enforced by Claude Code, not the prompt.** Every call runs with `--tools`,
  `--allowedTools`, `--disallowedTools`, `--permission-mode dontAsk`, `--setting-sources project` and
  `--strict-mcp-config`.
- **`build` cannot run `docker`.** `docker run -v /:/host` would escape the workspace.
- **A deny-list blocks read-only commands that leak host information** (`env`, `printenv`, `whoami`,
  `hostname`, `ps`, `ipconfig`, …), which Claude Code would otherwise auto-approve. Live-tested.
- **`--sandbox docker`** (on `run`, `exec` and `batch`) runs the agent and the test commands inside a
  throwaway container. Only the workspace is mounted; it runs unprivileged with all capabilities dropped and a read-only root filesystem (only `/tmp`
  and the home directory are writable, in memory).
  Set it up once:
  ```bash
  lattice sandbox-build                       # builds lattice-agent:0.1 (Claude Code 2.1.325, Node 22)
  claude setup-token                          # then: set CLAUDE_CODE_OAUTH_TOKEN=<token>
  ```
  The token is passed into the container by name (never on a command line). The agent inside can read it,
  so use one you can revoke.

See [docs/commands.md](docs/commands.md), [docs/safety.md](docs/safety.md) and
[docs/errors.md](docs/errors.md).

## Pong example

`apps/PONG-001/` was generated end to end by [`examples/pong.lat`](examples/pong.lat) with v0.2:
specify → build → test → verify → review. In that run, 36 tests and the production build passed, all
10 requirements were verified, and `review` flagged a real ball-tunnelling bug at high speed
(`src/game/logic.ts`). To play it:

```bash
cd apps/PONG-001 && npm install && npm run dev     # http://localhost:5173/
```

To regenerate it, move or delete `apps/PONG-001/` (otherwise `build` continues the existing code) and run
`py -m lattice run examples/pong.lat --replace`.

## License

MIT. See [LICENSE](LICENSE).
