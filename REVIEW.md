# Lattice v0.2: review brief (after refactor)

Please review critically. This is a refactor of Lattice v0.1 done by an AI coding agent (Claude Code) from a
refactor brief written by an earlier reviewer. Check whether each requested change was actually made, whether
anything regressed, and whether the safety claims hold.

## What Lattice is

A small scripting language for LLM agents. A `.lat` script is a sequence of command calls. The runtime turns
each into a tool-restricted Claude Code call (`claude -p`), validates the output (JSON Schema plus
deterministic checks against the real workspace and logs), retries once with the validation findings, and
records everything under `.lattice/`.

```python
spec = specify("A simple Pong game", constraints=["React + TypeScript + Vite, no backend"], id="PONG-001")
build(spec)
test(spec, run=["npm install", "npx vitest run --reporter=junit --outputFile=test-results/junit.xml"])
verify(spec)
review(spec, criteria=["correctness", "readability"])   # a project-defined command
```

## Requested changes and what was done

| Request | Done | Where |
|---|---|---|
| Remove the 17 generic commands, decision models, `deploy`, and the CRM/enterprise stack scaffolding | Yes. Also removed the native control commands (approve, checkpoint, rollback, package, report, validate) and the profiles system; `specify` takes free-text `constraints` instead. | deleted `lattice/registry/`, `profiles.py` |
| Directory-based command loader (`./commands/`, `~/.lattice/commands/`), defined by `<name>.yaml` + `<name>.md` | Yes. Load order built-in → user → project; later wins; overrides are reported. Optional `<name>.schema.json` or inline `output_schema`. Invalid definitions fail with file and reason. | `lattice/loader.py` |
| Keep 4–5 built-ins in the same plugin format | `specify`, `build`, `test`, `verify`, `research` | `lattice/commands/*.yaml/.md/.schema.json` |
| Bind outputs to variables and pass them on (`spec = specify(...)`, `build(spec)`), alongside `id=` | Yes. A bound variable passed as a value means its artifact id. | `lattice/script.py` |
| Property access (`spec.id`, `spec.output.summary`) without enabling code execution | Yes. Dotted refs parse to `Ref(name, path)` and are resolved as data lookups, not Python attributes. `_`-prefixed names, subscripts, method calls and nested calls are rejected. | `lattice/parser.py` |
| Keep `ast.parse` non-evaluating | Yes; 24 rejection cases tested | `tests/test_parser.py` |
| Remove `docker` from the `build` allow-list | Yes, and `Bash(docker:*)` is explicitly denied | `lattice/config.py` |
| `--sandbox docker` on `run`/`batch` running `claude -p` in an ephemeral container with only the workspace mounted | Yes (also on `exec`). Test commands also run in the container. Image `lattice-agent:0.1` (Node 22, Claude Code 2.1.325, user `node`); flags `--rm --cap-drop ALL --security-opt no-new-privileges`, plus pid, memory and cpu limits. The token is passed by env-var name only. | `lattice/sandbox.py`, `docker/Dockerfile` |
| Block unintended read-only auto-approvals with `--disallowedTools` | Yes, best-effort: a deny-list of information-leaking read-only commands. It is documented as a list, not a boundary. | `INFO_LEAK_DENY` in `lattice/config.py` |
| Remove `bench.py` and dead code | Yes (`bench.py`, suites, results, decision and stack validators) | — |
| `lattice commands` / `check` reflect loaded commands | Yes: source, overrides, searched directories; `check` validates definitions and tool policies | `lattice/cli.py` |
| Tests pass against the new loader, variable syntax and batch runner | **85 tests pass** | `tests/` |

## Decisions made during the refactor (approved by the user)

1. `test` gets its commands from the script (`run=[...]`), with npm/Vitest defaults in `test.yaml`. It never
   runs commands chosen by the agent.
2. Profiles were removed completely; `specify(constraints=[...])` replaces them.
3. The sandbox uses a revocable `claude setup-token` token passed by name. It is readable by the agent inside
   the container, and this is documented.
4. `review` survives as the example project command (`commands/review.*`). `requirement` and `design` merged
   into `specify`.

## Verified live (Claude Code 2.1.325, claude-sonnet-5-5)

- **`build` policy probe:** `whoami`, `env`, `docker ps` and `hostname` were all **denied**; `npm --version`
  was allowed. In v0.1, `whoami` had been auto-approved.
- **Container probe (free, no model):** only the workspace is visible; no host drive and no host `~/.claude`;
  uid 1000; `CapEff 0`; cannot write `/etc`. `sandbox.check()` correctly reports the missing token.
- **New `specify`:** passed on the first attempt in 23s; 6 requirements; both constraints restated and checked.

### After the follow-up hardening (also live, 2026-11-14)

- **Hardening:** missing dotted paths fail with the exact path; templates are checked for undefined
  `$placeholders`; the sandbox root filesystem is read-only (live: `/`, `/etc` and `/usr/local` refuse writes,
  while `npm install`, `npx` and `claude` still work).
- **Full Pong pipeline from an empty workspace:** specify → build → test → verify → review all passed on the
  first attempt in about 3.5 min. Lattice's own test run: 36 tests and the production build passed. `verify`
  covered all 10 requirements with checked evidence (verdict pass). `review` (the project command) found a
  real ball-tunnelling bug.
- **Live 3-way parallel research batch:** 3/3 completed in 36.5s, each first-attempt, with every cited URL
  verified against its own session.

## Not verified

- **No full agent run inside the sandbox yet.** It needs the user's `claude setup-token`. The launch path is
  tested by intercepting the real `Popen` call.
- **No live parallel *app* batch yet**, and nothing run with `--sandbox docker` end to end. Both need the
  user's token and are being run by the user.
- The sandbox still has network access (needed for the model API).

## Questions for the reviewer

1. Is dotted-reference resolution as data lookup, with `_` rejection and no subscripts, a sound replacement
   for Python attribute access?
2. Are there gaps in the plugin format: missing fields, or validation that `lattice check` should do but
   doesn't?
3. Is the container configuration adequate for running agent-written code? What would you add (network
   egress limits, read-only root, seccomp)?
4. Is anything left that is still over-built for a general-purpose LLM scripting runner?

## Map

```
lattice/parser.py      grammar + whitelist            lattice/loader.py     command plugins
lattice/script.py      variables, ids, resume         lattice/runtime.py    execute/validate/retry/persist
lattice/validators.py  built-in checks                lattice/procedures.py test runner + post hooks
lattice/sandbox.py     docker sandbox                 lattice/batch.py      parallel batches
lattice/commands/      built-in standard library      commands/             project commands (review)
```
