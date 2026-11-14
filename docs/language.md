# Script language

Quick reference. For an introduction to the language and every command, read [the Jig guide](guide.md).

Jig scripts use Python's syntax, but they are not Python. The parser accepts a fixed set of
constructs and the runner interprets them itself. Nothing is ever executed as Python. Only **command calls**
(`specify`, `build`, `research`, your own commands) call an agent and cost anything; everything else runs
locally.

```python
q = queue(intake.output.requirements)
done = map()
while len(q) > 0:
    req = q.pop()
    spec = specify(req.goal, id=req.id)
    build(spec)
    v = verify(spec)
    done[spec.id] = v.status
print(done)
```

## Statements

| Statement | Example |
|---|---|
| Command call | `build(spec, notes="retry")` |
| Assign a command result | `spec = specify("A notes app")`, `results[id] = build(spec)` |
| Assign a value | `n = 0`, `xs = []`, `m["k"] = v`, `a, b = pair` |
| Update | `n += 1`, `xs += [x]`, `m["count"] += 1` |
| Call a builtin or method | `print(x)`, `xs.append(x)` |
| `if` / `elif` / `else` | `if v.output.verdict == "pass":` |
| `for` | `for req in spec.output.requirements:`, `for i, x in enumerate(xs):`, `for k in m:` |
| `while` | `while v.status != "completed" and tries < 3:` |
| `break`, `continue`, `pass` | inside loops / anywhere |

A command call must be a statement of its own or the right side of an assignment, so every agent step is
visible in the script. `if verify(spec).status == ...` is rejected: assign first (`v = verify(spec)`).

## Expressions

- **Literals:** strings, numbers, `true`/`false`/`null` (or `True`/`False`/`None`), `[lists]`, `{"maps": 1}`.
- **Variables and data lookups:** `spec.id`, `spec.status`, `spec.output.summary`, `row.goal`, `xs[0]`,
  `m["key"]`, `xs[1:3]`, `xs[-1]`.
- **Operators:** `+ - * / // %`, comparisons `== != < <= > >=` (chains like `0 < n < 10` work), `in`,
  `not in`, `is None`, `and`, `or`, `not`, `a if test else b`.
  `+` joins strings or lists; mixing text and numbers needs `str()` or an f-string.
- **f-strings:** `f"attempt {n} of {len(xs)}"`.

## Command results

`x = command(...)` binds the whole result:

| Lookup | Value |
|---|---|
| `x` passed to a command | its artifact id: `build(spec)` |
| `x.id` | artifact id (or `null`) |
| `x.status` | `completed`, `failed`, `blocked`, `unavailable` |
| `x.output.<field>` | the command's checked output (see its `.schema.json`) |
| `if x:` | true when the step completed |

A failed step stops the script, unless you run with `--continue-on-error`. With that flag, the script can
handle the failure itself: `if r.status == "failed": ...`. Retry loops need the flag, because a `verify`
whose verdict is not a pass counts as a failed step. Its output (`v.output.verdict.result`, `v.output.items`)
is still available.

With `--continue-on-error`, the script decides the outcome. A failed step the script handles does not fail
the run (the count is in `step_failures`). Call `fail("reason")` to stop the script and mark the run
failed, for example when a game still does not pass after its fix rounds:

```python
if verdict != "pass":
    fail(f"{id}: still not passing after {fixes} fix(es)")
```

## Data types

All are local, free, and passed to commands as plain JSON (queues and sets become lists).

| Type | Make | Operations |
|---|---|---|
| list | `[]`, `list()`, `list(x)` | `append(x)`, `push(x)`, `pop()`, `pop(i)`, `insert(i, x)`, `extend(xs)`, `remove(x)`, `index(x)`, `sort()`, `sort(true)` (descending), `reverse()`, `copy()`, `xs[i]`, `xs[i] = v`, `xs[a:b]`, `+`, `*`, `in`, `len` |
| map | `{}`, `map()`, `map(pairs)` | `m[k]`, `m[k] = v`, `get(k)`, `get(k, default)`, `put(k, v)`, `has(k)`, `remove(k)`, `keys()`, `values()`, `items()`, `copy()`, `in`, `len`; looping gives keys in insertion order |
| queue | `queue()`, `queue(xs)` | `push(x)` adds at the back, `pop()` takes from the front, `peek()`, `copy()`, `in`, `len`; `if q:` is true while not empty |
| set | `set()`, `set(xs)` | `add(x)`, `remove(x)`, `has(x)`, `union(xs)`, `intersection(xs)`, `difference(xs)`, `copy()`, `in`, `len`; loops run in sorted order |
| string | `"..."`, `str(x)` | `lower()`, `upper()`, `strip()`, `split()`, `split(sep)`, `replace(a, b)`, `sep.join(xs)`, `startswith(s)`, `endswith(s)`, `contains(s)`, `s[i]`, `s[a:b]`, `+`, `in`, `len` |

A stack is a list (`append` / `pop`). Map keys and set items must be strings, numbers, booleans or null.

**Builtins:** `len`, `range`, `enumerate`, `sorted`, `min`, `max`, `sum`, `abs`, `round`, `str`, `int`,
`number` (alias `float`), `bool`, `type`, `print`, `fail`, plus the constructors `list`, `map` (alias `dict`),
`queue`, `set`. These names are reserved: they cannot be assigned, and a command with one of these names
would be shadowed.

`print(...)` output is shown by `jig run` (prefixed `|`) and returned in `--json` output under `log`.

## Limits

These stop runaway scripts. Set them in `jig.yaml`:

```yaml
script:
  max_while_iterations: 10   # a while loop whose condition is still true after this fails the script
  max_steps: 100000          # statements executed per run
  max_items: 100000          # longest list/map/queue/set/string
```

A `while` loop always has a cap, because every pass can be a paid agent call. For an explicit cap per loop,
use `for attempt in range(3):` with `break`, or put a counter in the condition.

Errors while the script runs (a wrong type, an index out of range, a limit) fail with `E_SCRIPT` and
the line number. A lookup of a missing field fails with `E_PARAM` and lists the fields that exist.

## Artifact ids, `--replace` and `--resume`

- `specify(goal, id="EXP-001")` creates exactly that id. Without `id=`, the id comes from the agent's
  `artifact_code` and the next free number (`PONG-001`, `PONG-002`, ...), so loops get fresh ids.
- Re-creating an existing id is refused. `--replace` archives the old artifact just before the step that
  re-creates it, so this works inside loops as well.
- `--resume` replays the previous run of the same script with the same variables. Steps are matched in the
  order they ran, by command and inputs. Completed steps are reused up to the first step that differs, and
  from there everything runs for real. That makes resume safe in loops, where the same call can appear more
  than once. Each run's step journal is in `.jig/scripts/<key>.json`.

## What is rejected

Imports, `def`, `class`, `lambda`, comprehensions, `with`, `try`, `del`, `global`, `:=`, `**`, `*args`,
`**kwargs`, method names outside the table above, and names starting with `_`. Each gives a positioned
`E_PARSE` error before anything runs.
