# The Jig guide

This guide explains the Jig scripting language and its commands from the beginning. You do not need to
know Python. For a quick reference, see [language.md](language.md) (the language),
[commands.md](commands.md) (how command definitions work) and [errors.md](errors.md) (error codes).

**Contents**

1. [What Jig is](#1-what-jig-is)
2. [Your first script](#2-your-first-script)
3. [Two kinds of lines](#3-two-kinds-of-lines)
4. [The commands](#4-the-commands)
5. [Using a command's result](#5-using-a-commands-result)
6. [The language](#6-the-language)
7. [When things fail](#7-when-things-fail)
8. [Running scripts](#8-running-scripts)
9. [Running many items at once](#9-running-many-items-at-once)
10. [Running again: --replace and --resume](#10-running-again---replace-and---resume)
11. [Where everything is saved](#11-where-everything-is-saved)
12. [Writing your own command](#12-writing-your-own-command)
13. [Limits and safety](#13-limits-and-safety)
14. [Worked example: the game factory](#14-worked-example-the-game-factory)
15. [Glossary](#15-glossary)

---

## 1. What Jig is

Jig is a small scripting language for giving work to AI agents in a controlled way. A script is a plan.
Some of its lines hand a task to an AI agent (Claude Code today), such as "write a spec", "build the
code" or "check every requirement". The rest of the script decides what happens next, based on the
checked results.

What makes Jig different from asking an agent directly:

- **Each step is boxed in.** A step can only use the tools its definition allows. For example, `verify`
  can read files but cannot change them.
- **Each answer is checked by code, not trusted.** The agent's output must match a fixed format, and
  then automatic checks run. For example: do the files it claims to have written exist? Do the tests it
  cites really exist in the test run?
- **Everything is recorded.** Every prompt, answer, check and cost is saved under `.jig/`.

The name comes from the workshop: a jig holds the work and guides the tool, so every piece comes out to
spec.

### How a script runs

Jig reads your script and *interprets* it, one statement at a time. Nothing is compiled, and nothing is
run as Python, even though the syntax looks like Python.

```
your script ──read──> list of statements ──interpreter──> plain logic (ifs, loops, lists)     free
                                                │
                                                └──> command step ──> AI agent or test runner  costs
                                                                            │
                                    result back to the script <── checks ───┘
```

Because the script runs step by step, a later step can depend on an earlier result. For example, the
script rebuilds only if `verify` found something missing.

---

## 2. Your first script

Save this as `pong.jig`:

```python
# A simple Pong game, built, tested and checked.
spec = specify("A simple Pong game: two paddles, a ball, first to 10, player vs computer",
               constraints=["React + TypeScript + Vite, no backend"], id="PONG-001")
build(spec)
test(spec, run=["npm install", "npx vitest run --reporter=junit --outputFile=test-results/junit.xml"])
verify(spec)
```

Run it:

```bash
py -m jig run pong.jig
```

What happens:

1. `specify` asks an agent to turn the one-line goal into a spec with numbered requirements. That
   creates the game's record, `PONG-001`.
2. `build` asks an agent to write the code in `apps/PONG-001/`.
3. `test` runs the commands you listed and reads the real results.
4. `verify` asks an agent to check every requirement against the code and the test results.

Each step prints its result as it finishes. The whole run takes a few minutes and is a paid agent run.

---

## 3. Two kinds of lines

A script mixes two kinds of lines.

**Commands are the steps.** There are five built in (`specify`, `build`, `test`, `verify`, `research`),
plus any you add yourself, such as `review` in this repo. Each one is defined by files that say what it
may do and what its answer must look like. Each run is recorded. All of them except `test` call an AI
agent.

**Everything else is ordinary language: free and instant.** This includes variables, text handling,
lists, `if`, loops, `print` and `fail`. It is the glue that decides which steps run and what they get.

```python
name = file.split(".")[0]      # language: "pong.md" -> "pong"           (free)
spec = specify(f"Build {name}", brief="requirements/" + file)   # command  (AI step)
if spec.status != "completed": # language: decide what to do next        (free)
    fail("specify failed")     # language: stop and mark the run failed  (free)
```

The rule of thumb: a line that calls a command is a step. Everything else is bookkeeping.

---

## 4. The commands

Every command is called the same way:

```python
command(target, name=value, name=value, ...)
result = command(target, ...)        # keep the result to use later
```

- The **target** is the one value without a name. It is the text to work on (`specify`, `research`) or
  the thing to work on (`build(spec)`).
- **Parameters** are the named values. A command only accepts the parameters it declares. A misspelled
  one is an error, caught before anything runs if you use the skill's checker.

Run `py -m jig commands` to see every loaded command and where it came from.

### `specify`: turn a goal into a spec

|  |  |
|---|---|
| **Does** | Writes a buildable spec: numbered requirements with testable checks, decisions, components, a test plan |
| **AI agent** | Yes. It has no tools; it only writes the spec. |
| **Target** | Text: the goal, e.g. `"A notes app with tags and search"` |
| **Creates** | A new artifact (the item's record), e.g. `NOTE-001` |

| Parameter | Meaning |
|---|---|
| `constraints=[...]` | Rules the spec must follow, e.g. `["React + TypeScript", "no backend"]`. Each must be restated in the spec, and this is checked. |
| `brief="path.md"` | A file with fuller requirements, inside the project. It is given to the agent as data, not as instructions. |
| `id="ABC-001"` | The exact id to create. Without it, the id comes from the agent's short code and the next free number. |

**Result fields** (`spec.output.<field>`): `title`, `summary`, `requirements` (each with `id` such as
`R-01`, `title`, `description`, `priority` = `must`/`should`/`could`, `acceptance`), `constraints_applied`,
`assumptions`, `decisions`, `components`, `test_plan`, `out_of_scope`, `artifact_code`.

### `build`: write the code

|  |  |
|---|---|
| **Does** | Implements the spec in the item's folder, with tests, and makes the tests pass |
| **AI agent** | Yes. It can read and write files in its own folder and run `npm`, `npx`, `node` and a few safe commands. It cannot run `docker` or `git push`, or read system information. |
| **Target** | The item, e.g. `build(spec)` |
| **Needs** | `specify` has completed for this item |

| Parameter | Meaning |
|---|---|
| `notes="..."` | Extra instructions for this build, e.g. a list of gaps to fix |
| `test_run=[...]` | The commands `test` will run afterwards; the build must make them pass |
| `path="dir"` | A different folder to build in (default `apps/<ID>/`) |

**Result fields:** `summary`, `files_created`, `requirements_implemented` (each with `requirement`,
`status` = `implemented`/`partial`/`not_implemented`, `evidence_paths`, `notes`), `commands_run`,
`known_gaps`, `run_instructions`.

**Checks:** every file it claims to have created must exist, and no secrets may appear in the folder.

### `test`: run the real tests

|  |  |
|---|---|
| **Does** | Runs your commands in the item's folder and reads the real JUnit test reports |
| **AI agent** | **No.** This step gives facts, not an opinion. |
| **Target** | The item |
| **Needs** | `build` has completed |

| Parameter | Meaning |
|---|---|
| `run=[...]` | Commands to run in order, e.g. `["npm install", "npx vitest run --reporter=junit --outputFile=test-results/junit.xml"]` |
| `expect_files=[...]` | Files that must exist afterwards, e.g. `["dist/index.html"]` |
| `reports=[...]` | Where to find JUnit XML reports (default `test-results/*.xml`) |
| `timeout_s=900` | Time limit in seconds |

**Result fields:** `passed` (true/false), `totals` (`tests`, `failures`, `errors`, `skipped`), `suites`.

**Checks:** at least one test must have run, and all must pass. Otherwise the step fails.

### `verify`: check every requirement

|  |  |
|---|---|
| **Does** | Checks each requirement against the code (with file and function evidence) and the recorded test results |
| **AI agent** | Yes. It can read files but not change them. |
| **Target** | The item |
| **Needs** | `specify` and `build` have completed |

No parameters.

**Result fields:** `summary`, `items` (one per requirement, each with `id`, `status` =
`satisfied`/`partial`/`not_satisfied`/`unverifiable`, `evidence`, `test_evidence`, `notes`), and
`verdict`.

**The verdict is decided by Jig, not by the agent.** `verdict.result` is `"pass"` only if every `must`
requirement is `satisfied` and the recorded tests passed. Otherwise it is `"fail"`,
`verdict.reasons` says why, and the step counts as failed (see [section 7](#7-when-things-fail)).

**Checks:** one item per requirement; every cited file exists; every cited function name appears in
that file; every cited test exists in the recorded test run.

### `research`: research a topic on the web

|  |  |
|---|---|
| **Does** | Searches the web and reports findings, each tied to a source |
| **AI agent** | Yes. Its only tools are web search and web fetch. |
| **Target** | Text (the topic), or an item |

| Parameter | Meaning |
|---|---|
| `question="..."` | A specific question about the topic |
| `min_sources=3` | The fewest distinct sources it must use |

**Result fields:** `summary`, `findings` (each with `id`, `claim`, `confidence`, `source_ids`), `sources`
(each with `id`, `url`, `title`, `excerpt`), `open_questions`, `method`.

**Checks:** every finding cites a listed source, there are enough sources, and every source URL really
appeared in the agent's own search and fetch results. Made-up links are rejected.

### `review`: review the code (a project command)

This command is defined in this repo's `commands/` folder. It also serves as the model for writing your
own.

|  |  |
|---|---|
| **Does** | Reviews the item's code against named criteria |
| **AI agent** | Yes. It can read files but not change them. |
| **Target** | The item |
| **Needs** | `build` has completed |

| Parameter | Meaning |
|---|---|
| `criteria=[...]` | What to judge, e.g. `["correctness", "readability", "security"]` (these three are the default) |

**Result fields:** `summary`, `criteria_assessed` (each with `criterion` and `rating` =
`pass`/`concerns`/`fail`), `findings` (each tied to a real file and line), `strengths`.

**Checks:** every criterion is assessed, and every finding points to a file and line that exist.

### Parameters every command accepts

| Parameter | Meaning |
|---|---|
| `max_attempts=N` | How many tries the agent gets (default 2; `build` gets 1, because a second try would run on top of half-written code) |

---

## 5. Using a command's result

Keep a result by assigning it: `spec = specify(...)`. You can then use:

| You write | You get |
|---|---|
| `spec` passed to a command | The item it created, e.g. `build(spec)` builds `PONG-001` |
| `spec.id` | The item's id, e.g. `"PONG-001"` |
| `spec.status` | How the step ended: `completed`, `failed`, `blocked` (a step it needs has not run) or `unavailable` (the agent could not start) |
| `spec.output.<field>` | Anything in the checked answer, e.g. `spec.output.summary`, `spec.output.requirements[0].id` |
| `if spec:` | True if the step completed |

Fields nest with dots and square brackets: `v.output.items[0].notes`, `v.output.verdict.result`. A
field that does not exist is an error that lists the fields that do, so typos are easy to spot.

---

## 6. The language

### Values and variables

```python
count = 3                         # a whole number
ratio = 0.5                       # a decimal number
name = "pong"                     # text (single or double quotes)
done = true                       # true / false (True / False also work)
nothing = null                    # no value (None also works)
STACK = ["React", "no backend"]   # a list
row = {"id": "PONG-001", "file": "pong.md"}   # a map (a set of named values)
```

Variable names use letters, digits and `_`, but cannot start with `_`. Built-in names such as `list` or
`len` cannot be reused as variable names.

### Arithmetic and comparisons

```python
n = 2 + 3 * 4          # 14     also: -  /  //  (whole division)  %  (remainder)
n += 1                 # add to a variable (also -=, *=, ...)
n > 10                 # true   also: == equal  != not equal  <  <=  >=
0 < n < 20             # true   comparisons can be chained
"b" in "abc"           # true   "in" also works on lists, maps and sets
x is None              # test for "no value"
n > 10 and done        # combine with and / or / not
"big" if n > 10 else "small"
```

### Text

```python
greeting = "Hello, " + name                  # join text with +
line = f"{name} has {count} levels"          # an f-string fills in values
"pong.md".split(".")                         # ["pong", "md"]
"pong.md".split(".")[0]                      # "pong"
"; ".join(["a", "b"])                        # "a; b"
name.upper()   name.lower()   name.strip()   name.replace("p", "P")
name.startswith("po")   name.endswith(".md")   name.contains("on")
len(name)   name[0]   name[1:3]
```

Text and numbers do not mix with `+`. Use `str(count)` or an f-string.

### Lists, maps, queues and sets

| Type | Good for | Make one | Common operations |
|---|---|---|---|
| **list** | an ordered collection | `[]`, `list()` | `xs.append(x)`, `xs.pop()`, `xs[0]`, `xs[-1]` (last), `xs[1:3]`, `xs.sort()`, `len(xs)`, `x in xs` |
| **map** | values looked up by name | `{}`, `map()` | `m["k"] = v`, `m["k"]`, `m.get("k", default)`, `m.has("k")`, `m.keys()`, `m.items()` |
| **queue** | work to do, first in first out | `queue()`, `queue(xs)` | `q.push(x)` (add at the back), `q.pop()` (take from the front), `q.peek()`, `len(q)` |
| **set** | unique values | `set()`, `set(xs)` | `s.add(x)`, `s.has(x)`, `s.union(xs)`, `len(s)` |

A stack (last in, first out) is a list: `append` to add, `pop` to take the last one. The full method
list is in [language.md](language.md#data-types). When you pass any of these to a command, it receives
plain data; queues and sets become lists.

### Decisions: `if`, `elif`, `else`

```python
if v.output.verdict.result == "pass":
    print("all good")
elif fixes < 2:
    print("try again")
else:
    fail("giving up")
```

The lines inside a block are indented (4 spaces is usual). The block ends where the indentation ends.

### Loops: `for` and `while`

```python
for file in ["pong.md", "snake.md"]:       # once per item in a list
    print(file)

for attempt in range(3):                   # 0, 1, 2: a fixed number of times
    if done:
        break                              # leave the loop early
    ...

for i, x in enumerate(["a", "b"]):         # with a position: 0 a, then 1 b
    print(i, x)

for key in m:                              # the names in a map
    print(key, m[key])

while len(q) > 0:                          # as long as something is true
    item = q.pop()
```

`continue` skips to the next pass of the loop. A `while` loop stops the script with an error after 10
passes by default, because each pass may be a paid agent call. Use `for attempt in range(N):` when you
want a fixed number of tries.

### Built-in functions

| Function | Does |
|---|---|
| `len(x)` | How many items or characters |
| `range(n)` | The list `0 ... n-1` (also `range(a, b)`) |
| `enumerate(xs)` | Pairs of position and item |
| `sorted(xs)`, `min(xs)`, `max(xs)`, `sum(xs)` | Sort, smallest, largest, total |
| `str(x)`, `int(x)`, `number(x)`, `bool(x)` | Convert to text, whole number, number, true/false |
| `abs(x)`, `round(x)` | Absolute value, rounding |
| `type(x)` | The kind of value: `"string"`, `"list"`, `"map"`, ... |
| `list()`, `map()`, `queue()`, `set()` | Make an empty one, or one from a list |
| `print(...)` | Write a line to the run log (shown with a `|` in front) |
| `fail("reason")` | Stop the script now and mark the run failed, with that reason |

### Variables from outside

A script can use variables it does not define, supplied when it runs:

```bash
py -m jig run research.jig --var topic="passkeys"          # one value
py -m jig run factory.jig --vars my-values.json            # many values from a JSON file
```

In a batch, each row of the batch file supplies the variables (see [section 9](#9-running-many-items-at-once)).

### Comments

Anything after `#` on a line is a comment for humans. Comment generously: say what each step is for,
and why each `if` and loop is there.

### What is not allowed

These are rejected, with the line number, before anything runs: `import`, defining functions (`def`) or
classes, `lambda`, `try`, `with`, `del`, list comprehensions, `**`, calling a command inside an expression
(such as `if verify(spec).status == ...`; keep the result first with `v = verify(spec)`), method names
that are not listed, and any name starting with `_`.

---

## 7. When things fail

### Inside a step: automatic checks and one retry

When an agent answers, Jig checks the answer against the command's format and runs its checks. If they
fail, the agent gets one more try with the problems listed. `build` does not retry automatically.
If it still fails, the step's status is `failed`, and the reasons are recorded.

### Between steps: a failed step stops the script

By default the first failed step stops the script, so nothing runs on top of a broken result.

### Handling failures yourself: `--continue-on-error` and `fail()`

To react to a failure, for example by rebuilding when `verify` finds gaps, run with
`--continue-on-error`. Then:

- A failed step does not stop the script. The script can look at `x.status` and decide what to do.
- **The script decides the outcome.** If it handles the failure and finishes, the run counts as
  completed. If it reaches a point where the result is not good enough, it calls `fail("reason")`, and
  the run counts as failed with that reason.

```python
v = verify(spec)
for attempt in range(2):
    if v.output.verdict.result == "pass":
        break
    build(spec, notes="fix what verify found")
    v = verify(spec)
if v.output.verdict.result != "pass":
    fail("still not passing")
```

A failed step's output is still available (`v.output.items`), so the script can see what went wrong.

### Script errors

Mistakes in the script itself, such as adding text to a number, reading past the end of a list or a
loop that never ends, stop the script with error `E_SCRIPT` and the line number. A field that does not
exist gives `E_PARAM`, with the list of fields that do. All codes are in [errors.md](errors.md).

---

## 8. Running scripts

```bash
py -m jig run script.jig                     # run a script
py -m jig run script.jig --var name=value    # supply a variable
py -m jig run script.jig --vars values.json  # supply variables from a file
py -m jig run script.jig --continue-on-error # let the script handle failed steps
py -m jig run script.jig --replace           # rebuild items that already exist (archives the old ones)
py -m jig run script.jig --resume            # continue an interrupted run
py -m jig run script.jig --sandbox docker    # run agents and tests in a throwaway container
py -m jig run script.jig --json              # full results as JSON
```

Other useful commands:

| Command | Does |
|---|---|
| `py -m jig exec 'research("passkeys")'` | Run a single command without a script |
| `py -m jig status` | Every item and its completed steps, plus anything running now |
| `py -m jig status PONG-001` | The steps of one item |
| `py -m jig show PONG-001 verify` | The full recorded result of one step |
| `py -m jig commands` | The loaded commands and where they come from |
| `py -m jig check` | Check all command definitions, the agent and the sandbox |
| `py -m jig errors` | All error codes |
| `py -m jig sandbox-build` | Build the Docker image for `--sandbox docker` |

To check a script for mistakes without running anything (it costs nothing):

```bash
py .claude/skills/jig-script/check.py script.jig --vars-file values.json
```

---

## 9. Running many items at once

When items are independent, such as three games, use a **batch**. You write two files:

- **A pipeline script** for one item. It uses variables such as `id` and `file` without defining them.
- **A batch file** (YAML) with one row per item, giving those variables:

```yaml
- {id: PONG-001,   file: pong.md}
- {id: TETRIS-001, file: tetris.md}
- {id: SNAKE-001,  file: snake.md}
```

```bash
py -m jig batch games.yaml --script game.jig --parallel 3 --continue-on-error
py -m jig batch-status games        # the summary table again later
```

- Each item runs as its own process, in its own folder and with its own ports, so items cannot interfere
  with each other.
- `--parallel 3` runs up to three at the same time.
- `--resume` skips items that already completed and continues the rest.
- The summary shows each item's status, time, reported cost and, for failures, the reason.

Use **one script with a loop** instead when items depend on each other, or when you want one combined
report at the end.

---

## 10. Running again: `--replace` and `--resume`

Running a script again would re-create items that already exist, so Jig refuses unless you say what you
want:

- **`--replace`** starts over. The existing item is archived (moved aside, not deleted) just before the
  step that re-creates it, and is then built again from scratch.
- **`--resume`** continues. Jig replays the previous run of the same script with the same variables.
  Steps that already completed with the same inputs are reused, and the first step that differs, and
  everything after it, runs for real. This also works inside loops.

---

## 11. Where everything is saved

| Location | Contents |
|---|---|
| `apps/<ID>/` | The item's working folder: the code `build` wrote |
| `.jig/artifacts/<ID>/manifest.json` | The item's current state: which steps completed |
| `.jig/artifacts/<ID>/stages/<step>/` | Every result each step ever produced |
| `.jig/runs/<run_id>/` | One step run: the exact prompt, the agent's event log and the result |
| `.jig/log.jsonl` | One line per step run |
| `.jig/scripts/` | Step journals used by `--resume` |
| `.jig/batches/<name>/` | Batch summaries and per-item results |
| `.jig/archive/` | Items moved aside by `--replace` |
| `jig.yaml` | Project settings (agent, model, time limits, script limits) |
| `commands/` | This project's own commands |

---

## 12. Writing your own command

A command is three files in `commands/` (for this project) or `~/.jig/commands/` (for all your
projects):

```
commands/draft.yaml          what the command is: parameters, tools, checks
commands/draft.md            the prompt given to the agent
commands/draft.schema.json   the exact format its answer must have
```

```yaml
# commands/draft.yaml
purpose: Write a business document from earlier findings; every claim must cite them.
version: "1.0.0"
target: {type: artifact_or_text, required: true}
parameters:
  kind: {type: string, description: "e.g. recommendation memo"}
  audience: {type: string, default: null}
artifact: optional
tool_policy: none            # none, read_workspace, research, write_workspace or build
validators: [unique_ids]
```

In the prompt, `$target` and each `$parameter` are filled in, and `$context` adds the results of the
item's earlier steps. Once the files exist, `draft(...)` works in any script. Run `py -m jig check` to
validate them. The full format, all placeholders and all available checks are in
[commands.md](commands.md). `commands/review.*` is a complete example.

---

## 13. Limits and safety

**Limits.** These stop runaway scripts and can be changed in `jig.yaml`:

```yaml
script:
  max_while_iterations: 10   # passes of a while loop before the script stops
  max_steps: 100000          # statements per run
  max_items: 100000          # longest list, map, queue, set or text
```

**Safety, in short.**

- Scripts are never run as Python. Only the listed features exist.
- Each command's agent gets only its allowed tools. For example, `build` cannot run `docker` or read
  system information, and `verify` and `review` cannot change files.
- Files and earlier results are given to agents as data, never as instructions.
- `--sandbox docker` runs agents and test commands in a throwaway container that can only see the item's
  folder.

The full safety model and its known limits are in [safety.md](safety.md).

---

## 14. Worked example: the game factory

[`factory/game.jig`](../factory/game.jig) builds one browser game from a requirements file, and
[`factory/games.yaml`](../factory/games.yaml) lists three games. This runs all three at once:

```bash
py -m jig batch factory/games.yaml --script factory/game.jig --parallel 3 --continue-on-error
```

For each game, the script:

1. **Settings.** Defines the rules every game follows (`STACK`), how to test (`TEST`) and how many fix
   rounds are allowed (`MAX_FIXES = 2`).
2. **Spec.** Turns `pong.md` into the name `pong` (text handling, free), then runs `specify` with the
   file as its `brief`. If that fails, it calls `fail()`: nothing can be built without a spec.
3. **Build, test, verify.** One AI step, one real test run, one AI check.
4. **Fix loop.** Up to two rounds. Each round collects every requirement verify did not find satisfied
   into a to-do list, such as `"R-02: score stops at 9"`, hands that list to `build` as `notes`, then tests
   and verifies again. The loop ends early as soon as everything passes.
5. **Review and outcome.** Reviews the code, prints a one-line summary, and calls `fail()` if the tests
   or the verdict still do not pass, so the batch summary shows exactly which games made it.

Every step is recorded, so `py -m jig show PONG-001 verify` shows the full evidence for each requirement.

---

## 15. Glossary

| Term | Meaning |
|---|---|
| **Script** | A `.jig` file: the plan, written in the Jig language |
| **Command** | A step defined by files (`specify`, `build`, ...). Most call an AI agent; `test` runs real tests. |
| **Item / artifact** | One thing being made, with an id such as `PONG-001`, a working folder and a record of its steps |
| **Target** | The unnamed first value of a command call: what it works on |
| **Parameter** | A named value in a command call, such as `notes="..."` |
| **Result** | What a command returns: `status`, `id` and `output` |
| **Output format (schema)** | The exact shape a command's answer must have; answers that do not match are rejected |
| **Checks (validators)** | Automatic tests on an answer, such as "the cited file exists" |
| **Verdict** | `verify`'s overall pass or fail, computed by Jig from the requirement statuses and the test results |
| **Batch** | Running one pipeline script for every row of a YAML file, in parallel |
| **Pipeline** | A script written for one item, meant to be run by a batch |
| **Tool policy** | Which tools a command's agent may use |
| **Sandbox** | An optional throwaway Docker container for agents and tests |
