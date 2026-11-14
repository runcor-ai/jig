---
name: jig-script
description: Write a Jig script (.jig), plus any batch file and custom commands it needs, from a plain-language ask. For example, "a software factory that builds apps from requirement files in a folder", "research these vendors and write a memo", or "an HR pipeline that drafts job descriptions". Use when the user asks for a Jig script, pipeline, factory, batch or workflow, or describes agent work to automate with Jig. Checks the result offline and never starts a paid run without asking.
---

# Writing Jig scripts from an ask

Jig scripts use Python syntax but are their own language. The runner interprets them, so only what
`docs/language.md` lists works. Read that file before writing anything non-trivial. It is the authority if
this skill and the docs disagree.

## 1. Pin down the ask

Work out these points from the request. Ask only about the ones you cannot infer, in one question:

- **Unit of work:** what one item is (a requirement file, a vendor, a topic, a contract).
- **Input source:** a list in the script, `--vars` JSON, or batch rows (YAML list, one row per item).
- **Output per item:** an app (specify/build/test/verify), research, or a business document.
- **Quality bar:** tests, verify, review criteria, how many fix attempts.
- **Parallel or sequential:** use batch for independent items in parallel, or one script with a loop when
  items depend on each other or need a combined report.

## 2. Use the commands that exist

Run `py -m jig commands` to see what is loaded. The built-ins are:

| Command | Target | Key parameters | Notes |
|---|---|---|---|
| `specify(goal)` | text | `constraints=[...]`, `brief="path/in/project.md"`, `id="ABC-001"` | Creates the artifact. `brief` is a file read as untrusted data. |
| `build(spec)` | artifact | `notes=`, `test_run=[...]`, `path=` | Writes code. |
| `test(spec)` | artifact | `run=[...]`, `expect_files=[...]`, `reports=`, `timeout_s=` | Runs commands, no agent. |
| `verify(spec)` | artifact | none | `v.output.items[*].status/id/notes`, `v.output.verdict.result` (`"pass"`). |
| `research(topic)` | text | `question=`, `min_sources=` | `r.output.summary`, `findings`, `sources`. |
| `review(spec)` | artifact | `criteria=[...]` | Project command in `commands/`. |

For any other step (draft, compare, assess, classify...), write a project command in `commands/`
(section 4). Never call a command that does not exist, and never pass a parameter it does not declare.
`check.py` catches both.

## 3. Language rules that matter most

- A command call is its own statement or `x = command(...)`. It is never inside an expression
  (`if verify(s).status` is rejected).
- `x` passed to a command means its artifact id. Read data with `x.status`, `x.id`, `x.output.<field>`.
- Control flow: `if/elif/else`, `for`, `while` (capped at `script.max_while_iterations`, default 10),
  `break`, `continue`. For bounded retries, use `for attempt in range(N):` with `break`.
- Data: `list`, `map`, `queue`, `set` and their methods; f-strings, `len`, `range`, `sorted`, `str`, `print`.
- **Failed steps stop the script.** Any loop that reacts to a failure (fix loops after `verify`, fallbacks)
  needs `--continue-on-error`. Write that flag into the run line in the header comment.
- No imports, functions, file listing or shell. Every file must be named in the script, the vars or the
  batch rows. Names starting with `_` are rejected.
- Ids look like `ABC-001`. Derive them from item names, e.g. `name.upper() + "-001"`; the name must be
  letters only.

## 4. Custom commands (when the ask needs them)

Write three files in `commands/<name>.*`. Follow `commands/review.*` and `docs/commands.md`:

```yaml
# commands/draft.yaml
purpose: Write <document kind> from <input>; every claim must cite the input it came from.
version: "1.0.0"
target: {type: artifact_or_text, required: true}
parameters:
  kind: {type: string, description: "e.g. recommendation memo"}
  audience: {type: string, default: null}
artifact: optional
tool_policy: none            # read_workspace if it must read files; research if it must use the web
validators: [unique_ids]
```

- `draft.md` is the prompt. Use `$target`, each `$param`, and `$context` for earlier stages. Wrap inputs in
  `<data name="...">` tags.
- `draft.schema.json` is a JSON Schema with `required` fields, so later script lines can rely on
  `x.output.<field>`.
- Run `py -m jig check` to validate the definitions.

## 5. Patterns

**Factory, from files in a folder** (sequential, with a combined report):

```python
# jig run factory/apps.jig --continue-on-error
FILES = ["pong.md", "tetris.md"]                      # in requirements/
STACK = ["React + TypeScript + Vite, no backend", "Vitest + @testing-library/react with jsdom for tests"]
TEST = ["npm install --no-audit --no-fund",
        "npx vitest run --reporter=junit --outputFile=test-results/junit.xml", "npm run build"]
report = map()
for file in FILES:
    name = file.split(".")[0]
    app_id = name.upper() + "-001"
    spec = specify(f"Build the app described in the brief ({name})", brief="requirements/" + file,
                   constraints=STACK, id=app_id)
    if spec.status != "completed":
        report[app_id] = "spec failed"
        continue
    build(spec, test_run=TEST)
    t = test(spec, run=TEST, expect_files=["dist/index.html"])
    v = verify(spec)
    for attempt in range(2):
        if v.output and v.output.verdict.result == "pass":
            break
        gaps = []
        for item in v.output.items:
            if item.status != "satisfied":
                gaps.append(f"{item.id}: {item.notes}")
        build(spec, test_run=TEST, notes="; ".join(gaps))
        t = test(spec, run=TEST, expect_files=["dist/index.html"])
        v = verify(spec)
    report[app_id] = {"tests": t.status, "verify": v.output.verdict.result if v.output else "none"}
print(report)
```

**Parallel variant:** write a per-item pipeline (variables come from the row) and a batch file:
`- {id: PONG-001, file: pong.md}`, run with `jig batch items.yaml --script pipeline.jig --parallel 3`.
`examples/pipelines/factory.jig` is the queue-driven version, with its vars in `examples/batches/factory.json`.

**Business function:** use `research` for facts, then custom commands for the domain step:

```python
market = research(category, question="Which vendors meet these needs, and at what price?", min_sources=5)
memo = draft(market, kind="recommendation memo", audience="CFO")
```

## 6. Check, then hand over

1. Run `py .claude/skills/jig-script/check.py <script.jig>`. Add `--var name` for each variable a batch
   row or `--vars` file supplies, or `--vars-file <file>`. Fix everything it reports.
2. If you wrote commands, run `py -m jig check`.
3. Report the files you wrote, the exact run command (with `--continue-on-error` when the script retries),
   and what each item costs. Each app is a paid agent run of several minutes; research is about a minute.
4. **Do not start a real run yourself.** Suggest the smallest first run (one item) and ask before running
   anything that calls an agent.
