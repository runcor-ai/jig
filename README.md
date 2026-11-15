# Jig v0.3

**Jig is a layer of abstraction for AI work.** The machinery for AI work is now strong: orchestration frameworks,
agent teams, and harnesses with deterministic hooks. What is missing is a level above it. The way of working is
spread across prompts in code, tool rules in configs, checks in hook scripts and coordination in agent messages,
so it is hard to read as a whole, every change touches the plumbing, success is often the agent's own report, and
the process is rarely a unit precise enough to be compared, repeated or measured.

Jig separates the **definition of the work** from the **mechanics of executing it**. The script says which steps
run, in what order, with which inputs and which agent. Each step's prompt, tools, answer format and checks are
written once, one level down, and the runtime runs them on whichever agent host the script names. Because a way of
working is then a precise, versioned definition that leaves the same record on every run, it can be run on many
cases, compared, taken apart and rated.

```python
spec = specify("A simple Pong game: two paddles, a ball, score to 10, player vs computer",
               constraints=["React + TypeScript + Vite, no backend"], id="PONG-001")
build(spec)
test(spec, run=["npm install", "npx vitest run --reporter=junit --outputFile=test-results/junit.xml"])
verify(spec)
```

**What is encapsulated.** Each step (`specify`, `build`, `test`, `verify`, `research`, or one you define) is a
contract written once: its prompt template, the tools its agent may use, the exact JSON shape of its answer, and the
checks run on that answer. A script never contains a prompt or a tool permission.

**What stays explicit.** The script: which steps run, in what order, with which inputs and which agent
(`agent="opus"`, `agent="luna"`), and what happens when a check fails. Every agent call is its own line. Plain logic
(`if`, `for`, lists) runs locally, and the script is never executed as Python.

**How correctness is enforced.** An answer is accepted only if it matches its schema and passes deterministic checks
against the real workspace and records: files it claims exist, functions it cites are in those files, tests it cites
really ran, sources it cites were really retrieved. `test` runs the real test commands with no model involved, and
the verify verdict is computed from the requirement statuses and the recorded test result. A failed check gets one
retry with the findings listed; then the step fails. Everything is recorded under `.jig/`.

**What it does not do.** The checks catch fabricated and missing evidence; they do not judge meaning, so whether the
result is *right* rests on the tests you supply. Tool limits are enforced by the agent host (Claude Code or Codex),
with a Docker sandbox for real isolation. How often a whole script gets it right is a separate question, measured
with [The Reality Engine](https://therealityengine.ca) in the paper's short experiment: Jig makes a way of working
measurable (versioned definitions, uniform per-step records, batches); the ratings themselves are computed outside
it. The details, with every claim tied to the code and a comparison with DSPy, LangGraph, MCP and skills:
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

Commands are plugins. The five built-ins use exactly the format you use to add your own.

**Website:** <https://runcor-ai.github.io/jig/>, with the guide, the thought paper
([Abstraction for AI Work](https://runcor-ai.github.io/jig/paper/), with a short experiment) and three games Jig
built that you can play.

## Quick start

Requirements: Python 3.11+ with `pyyaml` and `jsonschema`, and the `claude` CLI logged in. You also need
Node.js for the example apps, and Docker for `--sandbox docker`.

```bash
py -m pytest -q                                  # 131 offline tests, no model calls
py -m jig check                              # command definitions, agent, sandbox
py -m jig commands                           # loaded commands and where they came from
py -m jig run examples/pong.jig --replace    # build Pong (about 5 min)
py -m jig exec 'research("passkey adoption", question="How widespread in 2026?")'
py -m jig batch examples/batches/research.yaml --script examples/pipelines/research.jig --parallel 3
```

## Script language

New to Jig? Start with **[the Jig guide](docs/guide.md)**: the language and every command, from the
beginning. Quick reference: [docs/language.md](docs/language.md).

```python
q = queue(requirements)                       # supplied with --vars or by a batch row
while len(q) > 0:
    req = q.pop()
    spec = specify(req.goal, id=req.id)
    build(spec)
    v = verify(spec)
    for attempt in range(2):                  # bounded retries (run with --continue-on-error)
        if v.output.verdict.result == "pass":
            break
        build(spec, notes=v.output.summary)
        v = verify(spec)
```

- **Commands are the only steps that cost anything.** A call is `command(target, name=value, ...)`,
  either on its own or as `name = command(...)`. Everything else runs locally.
- **Control flow:** `if`/`elif`/`else`, `for`, `while` (always capped, `script.max_while_iterations`),
  `break`, `continue`.
- **Expressions:** arithmetic, comparisons, `and`/`or`/`not`, `in`, indexing and slices, f-strings,
  builtins (`len`, `range`, `sorted`, `str`, `print`, ...).
- **Data types:** `list`, `map`, `queue` and `set`, with a fixed set of methods (`append`, `pop`, `push`,
  `put`, `get`, `add`, ...). They are passed to commands as JSON.
- **Failed steps stop the script** unless you pass `--continue-on-error`. Retry loops need that flag,
  because a `verify` whose verdict is not a pass counts as a failed step. With the flag, the script
  decides the outcome: it calls `fail("reason")` when the run should count as failed.
- **Bound results:** `spec = specify(...)` keeps the whole result. Passing `spec` to a command means its
  artifact id. Lookups read its data: `spec.id`, `spec.status`, `spec.output.requirements[0].id`.
- **Never executed as Python.** `ast.parse` is used only as a grammar with a node whitelist, and the runner
  interprets it. Imports, `def`, `class`, `lambda`, comprehensions, `try`, `with`, unknown methods and names
  starting with `_` are rejected before anything runs. Size and step limits stop runaway scripts.
- **Re-running.** Re-creating an existing id is refused. `--replace` archives the old artifact first.
  `--resume` replays the previous run step by step and continues from the first step that differs,
  which also works inside loops.

## Commands

| Command | Kind | What it does |
|---|---|---|
| `specify(goal, constraints=[], brief=None, id=None)` | agent, no tools | Goal → requirements (R-01…), decisions, components, test plan. Every constraint must be restated. |
| `build(spec, notes=None, test_run=[...])` | agent, build tools | Implements the spec in `apps/<ID>/` and makes `test_run` pass |
| `test(spec, run=[...], reports=[...], expect_files=[])` | runs in Jig, no agent | Runs your commands and parses the real JUnit XML. No reports means fail. |
| `verify(spec)` | agent, read-only | Per-requirement status with file/symbol evidence and test citations, all checked. The verdict is computed by Jig. |
| `research(topic, question=None, min_sources=3)` | agent, web only | Sourced findings. Every cited URL must appear in the session's own searches or fetches. |
| `review(spec, criteria=[...])` | **project command** (`commands/review.*`) | An example of a user-defined command |

### Add your own command

Put a `<name>.yaml`, a `<name>.md` (prompt template) and a `<name>.schema.json` (output schema, or inline it
in the yaml) in one of these places:

- `./commands/`: this project
- `~/.jig/commands/`: all your projects (or `$JIG_USER_COMMANDS`)

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
- **Checks:** `validators:` and `postprocess:` take names of built-in checks. `jig check` lists unknown
  names and other definition errors, with the file and reason.

## Running many at once

```bash
jig batch examples/batches/apps.yaml --script examples/pipelines/app.jig --parallel 3
jig batch examples/batches/apps.yaml --script examples/pipelines/app.jig --resume
jig batch-status apps
```

- Each item runs in its own process and its own workspace, with its own ports.
- Shared files are locked, and IDs are claimed atomically.
- `--resume` skips items that completed and resumes the rest step by step.
- `--continue-on-error` is passed to every item's script, so fix loops work in batches too.

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
  jig sandbox-build                       # builds jig-agent:0.1 (Claude Code 2.1.325, Node 22)
  claude setup-token                          # then: set CLAUDE_CODE_OAUTH_TOKEN=<token>
  ```
  The token is passed into the container by name (never on a command line). The agent inside can read it,
  so use one you can revoke.

See [docs/commands.md](docs/commands.md), [docs/safety.md](docs/safety.md) and
[docs/errors.md](docs/errors.md).

## Mini-games factory

[`factory/game.jig`](factory/game.jig) builds one browser game from a requirement file: specify → build →
test → verify, then up to 2 fix rounds fed by what verify and the tests found, then review.
[`factory/games.yaml`](factory/games.yaml) lists three games (Pong, a falling-block puzzle, Snake), with
their requirements in [`requirements/`](requirements). This builds all three at the same time:

```bash
py -m jig batch factory/games.yaml --script factory/game.jig --parallel 3 --continue-on-error
py -m jig batch-status games
```

Each game lands in `apps/<ID>/` (for example `apps/PONG-001/`), with every step recorded under `.jig/`.

First run, 14 November 2026: all three completed side by side in 5.5 minutes (reported usage $2.50).

| Game | Requirements | Tests | Verdict | Fix rounds | Review findings |
|---|---|---|---|---|---|
| `PONG-001` | 11 (9 must) | 36 passed | pass | 0 | 4 low |
| `TETRIS-001` (falling blocks) | 13 (11 must) | 41 passed | pass | 0 | 2 low |
| `SNAKE-001` | 10 (8 must) | 26 passed | pass | 0 | 2 low, 1 info |

The fix loop was not needed in this run. The review still found real defects that the tests passed,
for example a Pong ball that can be bounced back after it has passed the paddle.
[Play them on the website](https://runcor-ai.github.io/jig/).

## Earlier Pong example

[`archive/PONG-001-v0.2/`](archive/PONG-001-v0.2) was generated end to end by
[`examples/pong.jig`](examples/pong.jig) with v0.2: specify → build → test → verify → review. In that
run, 36 tests and the production build passed, all 10 requirements were verified, and `review` flagged a
real ball-tunnelling bug at high speed (`src/game/logic.ts`). To play it:

```bash
cd archive/PONG-001-v0.2 && npm install && npm run dev     # http://localhost:5173/
```

## License

MIT. See [LICENSE](LICENSE).
