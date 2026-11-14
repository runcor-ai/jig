# Lattice v0.1

Lattice is a small, declarative command language for driving an AI agent (Claude Code today) through a
**validated** pipeline. You write a short script:

```python
requirement("Build a customer management application",
            stack=["Java", "React", "PostgreSQL"], standard="enterprise")
design("CRM-001")
build("CRM-001")
test("CRM-001")
review("CRM-001", criteria=["security", "architecture"])
verify("CRM-001", against="requirements")
```

Each command becomes a normalized invocation. The runtime checks its parameters against a schema,
resolves context from earlier artifacts, runs the agent inside an enforced tool boundary, validates the
output (JSON schema plus deterministic semantic checks, many against the real filesystem), and records
everything under `.lattice/`.

Lattice does not try to be the intelligence. It standardizes how the agent is **invoked, constrained and
evaluated**.

## Quick start

Requirements: Python ≥ 3.11 with `pyyaml` and `jsonschema`, the `claude` CLI (logged in), and Docker for
`test`.

```bash
pip install -e .[test]          # or: py -m lattice ... without installing
lattice check                   # registry, agent adapter and docker availability
lattice commands                # the 32-command vocabulary
lattice run examples/crm.lat    # the CRM demonstration
lattice status CRM-001          # stages, statuses, running commands
lattice show CRM-001 verify     # full stage record (output + validation findings)
lattice exec 'review("CRM-001", criteria=["security"])'
pytest                          # offline test suite (fixture adapter; no API cost)
```

## Example: the Pong game

`apps/PONG-001/` is a browser Pong game generated end to end by the four-line script
[`examples/pong.lat`](examples/pong.lat): requirement → design → build → test. Its 23 unit tests and the
production build pass.

**Play it** (needs Node.js 18+):

```bash
cd apps/PONG-001
npm install        # first time only
npm run dev        # then open http://localhost:5173/
```

| Key | Action |
|---|---|
| Space | Start, pause / resume |
| Arrow Up / W | Paddle up |
| Arrow Down / S | Paddle down |
| Restart button | New game |

You play the left paddle against the computer; first to 10 wins.

**Other commands** (run inside `apps/PONG-001`):

```bash
npm test           # run the tests
npm run build      # production build into dist/
npm run preview    # serve the production build
```

**Regenerate it from scratch** (takes about 5 minutes through Claude Code):

```bash
py -m lattice run examples/pong.lat --replace
```

`--replace` archives the existing PONG-001 records first. The game folder is overwritten by the new build.

## Running many at once

Write the pipeline once, list the items, run them in parallel:

```bash
lattice batch examples/batches/research.yaml --script examples/pipelines/research.lat --parallel 4
lattice batch examples/batches/apps.yaml     --script examples/pipelines/app.lat      --parallel 3
lattice batch examples/batches/apps.yaml     --script examples/pipelines/app.lat      --resume   # retry failures only
lattice batch-status apps
```

- **Items file**: a YAML list. Each row's fields (`id`, `goal`, `topic`, ...) become variables in the script,
  for example `research(topic, question=question)`.
- **Parallel**: each item runs as its own process, in its own folder, with its own ports. Shared records are
  file-locked and IDs are claimed atomically.
- **Resume**: items that completed are skipped. In the others, steps that already completed with the same
  inputs are skipped.
- **simple vs enterprise**: `standard: simple` with `stack: [React]` gives a small React + TypeScript app,
  tested with `npm` and no Docker. `standard: enterprise` with `stack: [Java, React, PostgreSQL]` gives the
  full stack with auth, audit and Docker.
- **No cost caps.** Cost is reported per run as Claude Code reports it; on a subscription this is usage, not a
  charge.
- **research** searches the web (WebSearch/WebFetch only, no file or shell access). Every finding must cite a
  source, and every cited URL must appear in that session's own searches or fetches, or the result fails.

## Architecture

```
script.lat ──parser (ast, whitelist; no eval)──► statements
          └─script runner (artifact-id binding, variables, halt on failure)
                    │ normalized invocation {command,target,parameters,context,controls}
                    ▼
             Runtime.execute ── registry (commands.yaml) ── params/target/requires checks
                    │            profiles.yaml (versioned, overridable) · decision_models.yaml
                    ├─ agent:     prompt template + JSON schema + tool policy ─► AgentAdapter (claude_code)
                    ├─ procedure: test runner (docker compose suites → JUnit XML / HTTP checks)
                    └─ native:    status, checkpoint, rollback, approve, package, report, deploy, validate
                    ▼
             validation: JSON schema → semantic validators → (retry with feedback if idempotent)
                    ▼
             Store (.lattice/): artifacts/<ID>/manifest + append-only stage records, runs/<run_id>/, log.jsonl
```

| Component | Files |
|---|---|
| Command library | `lattice/registry/commands.yaml`, `lattice/schemas/*.json`, `lattice/prompts/*.md` |
| Command runtime | `lattice/parser.py`, `lattice/runtime.py`, `lattice/script.py`, `lattice/store.py` |
| Agent adapter | `lattice/adapters/base.py` (interface), `claude_code.py`, `fixture.py` (tests only) |
| Evaluation layer | `lattice/validators.py`, `lattice/procedures.py` (test runner), `lattice/bench.py` |
| Profiles and decision models | `lattice/registry/profiles.yaml`, `lattice/registry/decision_models.yaml` |
| Project config | `lattice.yaml` (model, budgets, timeouts, tool policies) |

More detail: [docs/commands.md](docs/commands.md), [docs/safety.md](docs/safety.md),
[docs/evaluation.md](docs/evaluation.md), [docs/errors.md](docs/errors.md).

## Script language

A script is a sequence of `command(target?, name=value, ...)` statements, optionally bound with
`name = command(...)`. Arguments may only be literals (strings, numbers, booleans, `None`, lists, dicts) or
references to earlier bindings. Python's `ast` module is used only as a grammar: nothing is executed, and
attribute access, operators, imports, comprehensions, f-strings and nested calls are rejected with a
positioned error.

**Artifact IDs.** A creating command (`requirement`) followed by a literal id that does not exist yet
(`design("CRM-001")`) allocates exactly that id. Without one, the id is `<artifact_code>-NNN`, where the
agent proposes the code. Re-running a script that would re-create an existing id is refused
(`E_ARTIFACT_EXISTS`). `--replace` archives the old artifact first; nothing is deleted.

**Controls.** `approval_required=True` and `max_attempts=N` are accepted on any command.

## Result contract

```json
{"command": "requirement", "status": "completed", "artifact_id": "CRM-001", "output": {...},
 "validation": {"passed": true, "findings": [{"rule": "...", "severity": "warning", "message": "..."}]},
 "execution": {"model": "claude-sonnet-5-5", "duration_ms": 61234, "token_usage": {...}, "cost_usd": 0.41,
               "adapter": "claude_code", "attempts": 1, "run_id": "...", "permission_denials": [],
               "duration_ms_wall": 63001},
 "error": null}
```

`status` is one of `completed`, `failed`, `blocked` (a required stage is missing or failed),
`awaiting_approval` or `unavailable`. Execution metrics come from what the agent host reports and are
`null` when it reports nothing. They are never estimated.

## Honest limits of v0.1

- Only the six core commands have command-specific prompts, schemas and validators that are exercised end
  to end. The other agent commands run on the shared generic path; the native commands are implemented.
  `deploy` records the approval check and then returns `E_UNAVAILABLE`, because no deployment integration
  ships.
- Validators check structure, traceability and that cited files, symbols and tests exist. They cannot prove
  that code is correct. That is what `test` (real test execution) is for, and it is still not proof of
  production readiness.
- The tool boundary is enforced by Claude Code's permission system. Claude Code also auto-permits commands
  it classifies as read-only (e.g. `whoami`), and the `build` policy allows `docker`, which can run
  arbitrary containers. See [docs/safety.md](docs/safety.md).
