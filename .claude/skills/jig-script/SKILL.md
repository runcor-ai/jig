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
- **Parallel or sequential:** independent items run at the same time, either with a script command and
  `each=` (section 4b, preferred when a script should collect the results) or with `jig batch`. Use one
  script with a loop when items depend on each other.
- **Reuse:** if the per-item work already exists as a script (e.g. `factory/game.jig`), call it as one step
  rather than copying its steps (section 4b).

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
| `make_game(file)` | text | `id=`; or `each=[...]`, `parallel=` | Project script command: runs `factory/game.jig` as one step. |

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
  needs `--continue-on-error`, on `jig run` and on `jig batch`. Write that flag into the run line in the
  header comment. With the flag, the script decides the outcome: end with
  `if <not good enough>: fail("reason")`, so a run only counts as completed when the result is good.
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

## 4b. A script as one step (a Jig calling a Jig)

A whole Jig script can be a command. Use this when the per-item work is already a script, or is long
enough that the top-level script should read as a few lines. One `.yaml` file, no prompt or schema file:

```yaml
# commands/make_game.yaml
purpose: Build one browser game from a requirements file, with tests, verify, fix rounds and review.
version: "1.0.0"
mode: script
script: factory/game.jig                         # relative to the project
target: {type: text, required: true, as: file}   # the target becomes the script's variable `file`
parameters:
  id: {type: string}                             # each parameter becomes a variable of the same name
continue_on_error: true                          # needed when the inner script has a fix loop
artifact: none
output_schema:
  type: object
  required: [id, tests, verdict]
  properties: {id: {type: string}, tests: {type: string}, verdict: {type: string}}
```

- The inner script hands back whatever it assigns to `result`, e.g.
  `result = {"id": id, "tests": t.status, "verdict": verdict}`. Set it **before** any final `fail()`, so a
  failing item still reports what happened. The keys must match `output_schema`.
- The inner script may use only the target variable and the parameters; the loader rejects anything else.
- One item: `r = make_game("pong.md", id="PONG-001")`, then `r.status`, `r.output.verdict`.
- Many items at the same time: `results = make_game(each=ITEMS, parallel=3)`, where each item is a map of
  the target variable and parameters (`{"id": "PONG-001", "file": "pong.md"}`). Each item runs in its own
  process; the line waits for all and gives a list of results in order. One failed item does not stop the
  others. `each=` works only with script commands.
- Run the outer script with `--continue-on-error` when it should read failed items rather than stop.
- Scripts nest at most `script.max_depth` deep (default 3).

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

**Parallel variant** (independent items at the same time): write a per-item pipeline (variables come from
the row) and a batch file, `- {id: PONG-001, file: pong.md}`. Run it with
`jig batch items.yaml --script pipeline.jig --parallel 3 --continue-on-error`. `factory/game.jig` with
`factory/games.yaml` is the worked example, and ends with `fail()` when a game still does not pass.
`examples/pipelines/factory.jig` is the queue-driven version, with its vars in `examples/batches/factory.json`.

**Factory over a script command** (all items at the same time, results collected in the script).
`factory/factory.jig` is the worked example:

```python
# jig run factory/factory.jig --continue-on-error
GAMES = [{"id": "PONG-003", "file": "pong.md"},
         {"id": "TETRIS-002", "file": "tetris.md"},
         {"id": "SNAKE-002", "file": "snake.md"}]
results = make_game(each=GAMES, parallel=3)
passed = []
for r in results:
    if r.status == "completed":
        passed.append(r.output.id)
    elif r.output and "tests" in r.output:
        print(f"{r.output.id} needs a look: tests {r.output.tests}, verify {r.output.verdict}")
if len(passed) != len(GAMES):
    fail(f"{len(GAMES) - len(passed)} game(s) did not pass")
```

**Business function:** use `research` for facts, then custom commands for the domain step:

```python
market = research(category, question="Which vendors meet these needs, and at what price?", min_sources=5)
memo = draft(market, kind="recommendation memo", audience="CFO")
```

## 6. Comment it for a non-programmer

Every script must be readable by someone who has never seen Jig:

- **Header block:** what the script makes, the exact run command, where the variables come from, the
  steps in plain words, which steps call an AI agent (and cost money) and which are free, and why any
  flag such as `--continue-on-error` is needed.
- **A section banner per stage** (`# ── Step 2: build it ──`), with one or two lines on what that step
  does and what its result is used for.
- **A comment above every `if`, loop and `fail()`** saying why it is there, in plain words, with a
  concrete example where it helps (`# e.g. "R-02: score stops at 9"`).
- Avoid jargon such as "artifact", "bound result" or "schema" in comments. Say "the game's folder",
  "the result", "the agreed format".
- Comment the batch file too: what a row is, what each field means, and how to add an item.

`factory/game.jig` and `factory/games.yaml` show the expected level.

## 7. Check, then hand over

1. Run `py .claude/skills/jig-script/check.py <script.jig>`. Add `--var name` for each variable a batch
   row or `--vars` file supplies, or `--vars-file <file>`. Fix everything it reports. For a script that a
   script command runs, pass its target variable and parameters, e.g. `--var file --var id`.
2. If you wrote commands, run `py -m jig check`. It also checks that each script command's script exists
   and uses only the variables the command passes it.
3. Report the files you wrote, the exact run command (with `--continue-on-error` when the script retries),
   and what each item costs. Each app is a paid agent run of several minutes; research is about a minute.
   With `each=`, items run at the same time, so time is about one item's, cost is the sum.
4. **Do not start a real run yourself.** Suggest the smallest first run (one item) and ask before running
   anything that calls an agent.
