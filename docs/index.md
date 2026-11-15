---
title: Jig
---

# Jig

**The AI control plane: define the work once, and every step is permitted, verified and measured, whoever
does it.**

Orchestration frameworks manage how agents run and coordinate. Jig sits above them. You describe the work in a
short script of steps, such as `specify`, `build`, `test` and `verify`. Each step runs under a contract written
once, one level down: its instructions, the tools it may use, the exact format of its answer, and the code checks
that run before anyone can use the answer. Every step is recorded, so a way of working can be run on many cases
and rated.

A step can be done by an AI model (`agent="opus"`, `agent="luna"`), by plain code (`test` runs the real tests),
or by another Jig script. Human experts as a worker are planned. A whole game factory is a few lines over one
step, `make_game`, which is itself a Jig script:

```python
GAMES = [{"id": "PONG-003", "file": "pong.md"},
         {"id": "TETRIS-002", "file": "tetris.md"},
         {"id": "SNAKE-002", "file": "snake.md"}]

results = make_game(each=GAMES, parallel=3)     # game.jig, once per game, all at the same time
for r in results:
    if r.status != "completed":
        print(f"{r.output.id} needs a look")
```

Each game runs [factory/game.jig](https://github.com/runcor-ai/jig/blob/master/factory/game.jig): specify,
build, the real tests, every requirement verified against the code, up to two fix rounds, and a review. On
14 November 2026 the three games were built at the same time in 5 minutes, and all passed.

## Read

| | |
|---|---|
| **[The Jig guide](guide.md)** | Start here: the language and every command, from the beginning |
| **[Abstraction for AI Work](paper/)** ([PDF](paper/Abstraction-for-AI-Work.pdf)) | A thought paper: why AI work cannot scale while the way of working is buried in the plumbing, and what a layer of abstraction must separate, check and measure, with a short experiment measured by [The Reality Engine](https://therealityengine.ca) |
| [Language reference](language.md) | Every statement, operator, data type and builtin |
| [Commands](commands.md) | How commands are defined, and how to add your own |
| [Safety model](safety.md) | Tool boundaries, the sandbox and known limits |
| [Error codes](errors.md) | Every error and what it means |

## Try it

```bash
git clone https://github.com/runcor-ai/jig && cd jig
py -m pytest -q                      # offline tests, no model calls
py -m jig check                      # command definitions, agent, sandbox
py -m jig run factory/factory.jig --continue-on-error              # the three games, at the same time
```

Requirements: Python 3.11+ with `pyyaml` and `jsonschema`, the `claude` CLI logged in, and Node.js for
the games. A full game build is a paid agent run of a few minutes.

Source and examples: **<https://github.com/runcor-ai/jig>** · MIT licence
