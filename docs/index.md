---
title: Jig
---

# Jig

**Work with AI at the right level: requirements, steps, results and checks, not prompts and tokens.**

A biologist explaining how a heart pumps does not talk about quantum physics. Every field controls
complexity by working at the right level of description. Jig does that for AI work. You describe the work
in a short script, as steps such as `specify`, `build`, `test` and `verify`. Each step keeps the detail
below it out of sight: its instructions to the agent, the tools it may use, the format its answer must
have, and the code checks that run before anyone can use the answer. Everything is recorded.

```python
spec = specify("Build the browser game described in the brief", brief="requirements/pong.md",
               constraints=["React + TypeScript + Vite, no backend"], id="PONG-001")
build(spec)
test(spec, run=["npm install", "npx vitest run --reporter=junit --outputFile=test-results/junit.xml"])
v = verify(spec)                     # every requirement checked; the verdict is computed by code
if v.output.verdict.result != "pass":
    build(spec, notes=v.output.summary)
```

## Play what it made

These three games were built side by side by Jig's game factory, in 5.5 minutes, from three short
requirement files. Each passed its real tests and had every requirement verified against the code:

| Game | Requirements | Tests | Play |
|---|---|---|---|
| Pong | [pong.md](https://github.com/runcor-ai/jig/blob/master/requirements/pong.md) | 36 passed | **[Play Pong](play/pong/)** |
| Falling blocks | [tetris.md](https://github.com/runcor-ai/jig/blob/master/requirements/tetris.md) | 41 passed | **[Play falling blocks](play/tetris/)** |
| Snake | [snake.md](https://github.com/runcor-ai/jig/blob/master/requirements/snake.md) | 26 passed | **[Play Snake](play/snake/)** |

The script that made them: [factory/game.jig](https://github.com/runcor-ai/jig/blob/master/factory/game.jig).
The code review still found small defects in each.

## Read

| | |
|---|---|
| **[The Jig guide](guide.md)** | Start here: the language and every command, from the beginning |
| **[Abstraction for AI Work](paper/)** ([PDF](paper/Abstraction-for-AI-Work.pdf)) | A thought paper: why AI work cannot scale through prompts and orchestration scripts, and what a layer of abstraction must separate, check and measure, with a short experiment measured by [The Reality Engine](https://therealityengine.ca) |
| [Language reference](language.md) | Every statement, operator, data type and builtin |
| [Commands](commands.md) | How commands are defined, and how to add your own |
| [Safety model](safety.md) | Tool boundaries, the sandbox and known limits |
| [Error codes](errors.md) | Every error and what it means |

## Try it

```bash
git clone https://github.com/runcor-ai/jig && cd jig
py -m pytest -q                      # offline tests, no model calls
py -m jig check                      # command definitions, agent, sandbox
py -m jig batch factory/games.yaml --script factory/game.jig --parallel 3 --continue-on-error
```

Requirements: Python 3.11+ with `pyyaml` and `jsonschema`, the `claude` CLI logged in, and Node.js for
the games. A full game build is a paid agent run of a few minutes.

Source and examples: **<https://github.com/runcor-ai/jig>** · MIT licence
