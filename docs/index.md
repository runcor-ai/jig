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

Jig's game factory builds a browser game from a short requirements file: spec, code, real tests, every
requirement checked against the code, up to two fix rounds, and a code review. It has built the same three
games twice, from the same requirement files:

| Game | Requirements | Version 1 | Version 2 |
|---|---|---|---|
| Pong | [pong.md](https://github.com/runcor-ai/jig/blob/master/requirements/pong.md) | 36 tests passed · **[Play](play/pong/)** | 48 tests passed · **[Play](play/pong-v2/)** |
| Falling blocks | [tetris.md](https://github.com/runcor-ai/jig/blob/master/requirements/tetris.md) | 41 tests passed · **[Play](play/tetris/)** | 31 tests passed · **[Play](play/tetris-v2/)** |
| Snake | [snake.md](https://github.com/runcor-ai/jig/blob/master/requirements/snake.md) | 26 tests passed · **[Play](play/snake/)** | 21 tests passed · **[Play](play/snake-v2/)** |

Every game passed its tests and had every must-have requirement verified, with no fix rounds needed. The
code review still found small defects in each, and the two versions differ: the requirements fix what a
game must do, not how it is written.

- **Version 1** came from a batch run of the one-game script,
  [factory/game.jig](https://github.com/runcor-ai/jig/blob/master/factory/game.jig): 5.5 minutes for all three.
- **Version 2** came from [factory/factory.jig](https://github.com/runcor-ai/jig/blob/master/factory/factory.jig),
  a Jig script that calls `game.jig` as one step for all three games at the same time: 5.0 minutes, $1.99.

```python
GAMES = [{"id": "PONG-003", "file": "pong.md"},
         {"id": "TETRIS-002", "file": "tetris.md"},
         {"id": "SNAKE-002", "file": "snake.md"}]
results = make_game(each=GAMES, parallel=3)     # game.jig, once per game, all at once
```

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
