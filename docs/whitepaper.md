---
title: "Abstraction for AI work"
---

# Abstraction for AI work

**Controlling complexity by working with AI at the right level, and proving that level holds at scale**

*White paper · Draft v0.1 · 14 November 2026 · LLM Jester*
*Companion to [Jig](https://github.com/runcor-ai/jig) and [The Reality Engine](https://therealityengine.ca)*

---

## Summary

A biologist explaining how a heart pumps does not talk about quantum physics. Quantum physics is not
wrong, and it is not irrelevant. Every heartbeat depends on it. But at the level of cells, muscles and
blood, the detail below is summed up in a few reliable rules, and working at that level is what makes the
problem possible to think about at all. Science handles complexity this way: each level of description has
its own vocabulary, and it can be trusted as long as the level below behaves as the level above assumes.

Work with AI today has no such levels. Every interaction is at the bottom: prompts, tool permissions,
tokens, model versions and the agent's own account of what it did. That is like doing biology in quantum
physics. It works for one small thing. It does not scale to many people, many tasks and many kinds of work.

This paper argues for **abstraction**, a higher level of description for AI work, and describes one:

- **[Jig](https://github.com/runcor-ai/jig)** gives AI work its own vocabulary: *requirements*, *steps*,
  *results* and *checks*. A person writes `build(spec)` or `verify(spec)` and reads `v.status` and
  `v.output.verdict`. The prompts, tools, retries and records are kept below that level, inside definitions
  written once. Interactions become simple enough to reason about, share and repeat.
- **[The Reality Engine](https://therealityengine.ca)** supplies what every abstraction needs: evidence
  that it holds. It tests AI systems "the way science tests ideas", on unseen cases with rules fixed in
  advance, and measures how often a system stays within tolerance and why it fails. Its first study found
  that the way information is written down moves a small model from 49% to 65% correct on sealed questions.

The two belong together. Jig makes AI work simple enough to do at scale. The Reality Engine shows, with
measurement rather than opinion, that the simple level can be trusted: that when a step says "built and
verified", that is true often enough, on work never seen before, to rely on.

---

## 1. The problem is complexity, not capability

Modern AI agents are capable. Given a one-line brief, an agent can produce a working browser game in a few
minutes. The difficulty is everything around that capability. To use an agent well today, a person has to
manage:

- the wording of the prompt, and how it changes the result;
- which tools the agent may use, and what it could do with them;
- whether its report ("all tests pass") is true;
- what happened when something went wrong, and why;
- how often the same request gives a good result, and on which kinds of input;
- which model, version and settings were used.

Each item is manageable on its own. Together, across many tasks, people and teams, they are not. The usual
answer is to tune by opinion: change a prompt, try a few demos, keep what looks better. A good demo does
not make a reliable system, and a system nobody can reason about cannot be made reliable.

The limiting factor is not what the model can do. It is how much complexity a person must hold in mind to
use it.

---

## 2. Levels of description

Every mature field controls complexity in the same way.

| Field | Lower level | Higher level | What the higher level says |
|---|---|---|---|
| Science | Quantum physics | Chemistry, then biology | "This enzyme speeds up this reaction" |
| Computing | Transistors, machine code | Programming languages | "Sort this list" |
| Engineering | Material behaviour | Components with ratings | "This bolt holds 10 kN" |
| Manufacturing | How each machine works | Stations with a spec and a quality check | "This part meets drawing 42, tolerance ±0.1 mm" |

Three things make a level useful.

1. **Its own vocabulary.** It talks about the things that matter at that level (cells, functions, parts),
   not about the detail underneath.
2. **Hidden detail.** The lower level is not removed. It is summed up in rules the higher level can rely
   on. You can always go down to look, but you do not have to.
3. **Known limits.** A higher-level rule holds *within tolerance*: a bolt is rated, a chemical rule holds
   over a range of conditions. Outside those limits the abstraction breaks, and knowing where it breaks is
   part of the knowledge.

The third point is the one most often missed. An abstraction is only as good as the evidence that the
level below behaves as promised. Biology can ignore quantum physics because, at biological scales,
chemistry has been measured to behave reliably.

---

## 3. A level of description for AI work: Jig

Jig is a small scripting language that gives AI work a higher level. A Jig script talks only about the
things a person cares about:

```python
spec = specify("Build the browser game described in the brief", brief="requirements/pong.md",
               constraints=["React + TypeScript + Vite, no backend"], id="PONG-001")
build(spec)
t = test(spec, run=["npm install", "npx vitest run --reporter=junit --outputFile=test-results/junit.xml"])
v = verify(spec)
if v.output.verdict.result != "pass":
    build(spec, notes=v.output.summary)
```

The words at this level are **requirement** (what is wanted), **step** (`specify`, `build`, `test`,
`verify`, `review`, or one a team adds itself), **result** (`v.status`, `v.output`) and **check** (did it
meet the bar?). The script says nothing about prompts, tool permissions, model settings, retries or log
files. Those still exist, one level down, written once in each step's definition.

### 3.1 What the level hides

Each step is defined by plain files that sum up the detail below it:

| Kept below the level | Where it lives |
|---|---|
| The exact instructions to the agent | the step's prompt template |
| What the agent may do | the step's tool policy: for example, `verify` may read code but not change it, and `build` cannot run `docker` or read system information |
| What a good answer looks like | the step's answer format, which every answer must match |
| How the answer is checked | the step's code checks, which run before anyone can use the answer |
| What to do when an answer fails a check | one retry, with the problems listed |
| What happened | a complete record of every prompt, answer, check and cost |

A person working at the higher level does not need any of this to write or read a script. Someone who does
need it can go down a level and look, as a biologist can consult chemistry.

### 3.2 What the level guarantees

A level of description is only worth having if its statements are reliable. Jig backs each statement with
code, not with the agent's word:

- **"Built"** means the files the agent says it created exist, and no secrets were written.
- **"Tested"** means the real test commands ran and the real test reports say they passed. No AI is
  involved in this step: it gives facts, not an opinion.
- **"Verified"** means every requirement was checked against the code, every cited function was found in
  the file named, and every cited test exists in the recorded test run. The verdict is computed by code:
  "pass" only if every must-have requirement is satisfied and the tests passed.
- **"Researched"** means every finding cites a source the agent actually retrieved; made-up links are
  rejected.

### 3.3 Simple interactions, deliberately

The language is small on purpose. Scripts have plain logic (ifs, loops, lists, text) for deciding what
happens next, and nothing else: no imports, no functions, no file access, and they are never run as
Python. Only a step can reach an AI agent, and a step is always its own line, so every AI interaction is
visible to a reader. Limits stop runaway loops, and a script can call `fail("reason")` to say a result was
not good enough. Keeping the interactions this simple is what keeps the work understandable as it grows.

---

## 4. What working at this level makes possible

**Scale.** One script serves any number of items. The game factory in the Jig repository builds a game
for every requirement file in a list. Each game runs at the same time, in its own process and folder, with
its own record.

**Shared understanding.** A script reads like a description of the work. A manager, a reviewer and an
engineer can all read the same script and agree on what it does.

**Change at one level without disturbing another.** The model behind a step, the wording of its prompt
or the strictness of its checks can change underneath while every script above stays the same. A new list
of requirements runs through the same script unchanged.

**Many kinds of work, one vocabulary.** The same steps combine into different functions: a software
factory, a vendor evaluation (research, then a recommendation memo), a contract review, a hiring pipeline.
New steps are added the same way the built-in ones are made.

**Locating problems.** When something goes wrong, it is found at a step, with its record, rather than
somewhere inside a long conversation with an agent.

---

## 5. Every abstraction needs evidence that it holds

A higher level is only safe to work at if its rules hold within known limits. For AI work, that raises
questions Jig alone cannot answer:

- When `verify` says "pass", how often is the result really good? Jig's checks catch fabricated files,
  functions, tests and sources, but they test *consistency*, not quality, and `verify` is itself an AI
  judgment wrapped in code checks.
- How often does a given step definition produce a result within tolerance, and on which kinds of input
  does it fail?
- When someone changes a step's prompt, is the new version really better, or did it look better on a few
  examples?

One successful build is an anecdote. A level of description earns trust the way chemistry did:
through measurement, on cases that were not chosen to make it look good. That is what the Reality Engine
does.

---

## 6. The Reality Engine

The Reality Engine is "a method for testing AI systems the way science tests ideas". It runs every
option on the same unseen cases, with the rules fixed in advance, to learn by experiment, not opinion, how
often a system gets it right, why it fails, and which change would make it better. Its starting point is
the problem of section 1: "AI systems are tuned by opinion", and "a good demo doesn't make a reliable
system."

**The method has seven steps:**

1. **Define** a *problem pack*: what a candidate is, how test cases are made, how results are scored, what
   "within tolerance" means, and what stays sealed.
2. **Lock** the rules by fingerprinting them before the first result. Any change needs a logged decision
   and a new lock.
3. **Compare** every candidate, the current setup among them as the control, on the same cases, with 95%
   ranges. Statistical corrections stop luck among many candidates from passing as skill.
4. **Take the winner apart**: split it into parts, have a designer that never sees test cases write an
   alternative for each part, and test every combination.
5. **Build out**: write new versions, screen each on fresh cases against a fixed bar, and confirm the
   promising ones in combination.
6. **Confirm** the final design against the control and its rivals on **sealed** cases, opened once.
7. **Report**: a trust report with six numbers. How often it is right, reliability, why it fails, the
   verdict, how hard it looked, and the headroom left.

**A change must earn its place twice.** It is kept only if its own effect is clearly positive and the
design it gives then beats the current best head to head. Picking the highest raw score would reward luck,
the "winner's curse".

**It is built to be honest.** The rules are locked in advance. The designer never sees test cases, answer
keys or sealed results. Every candidate faces the same cases. Failures count, scored as zero and never
dropped. Nothing is deleted.

**The first case study, *Describing Reality for AI***, tested fifteen ways of writing a system down for a
small model (GPT-6 Luna) to reason from. On 720 sealed items, short plain facts (FACTS) scored **0.654**
against **0.491** for plain prose notes, a lead of **+0.163** (95% range 0.140 to 0.186). Taking the winner
apart and building out 20 new versions found nothing that proved better. The study ran 43,995 test runs in
51 hours on one workstation. It states its limits plainly: one model, one AI judge, one designer, and
generated systems. On realistic AI-written documents, no format did much better than prose.

That result is itself about levels of description. *How a system is written down* for an AI, in short
plain facts rather than prose, changed how well the AI could reason about it, by a measured amount.

---

## 7. How they fit together

Jig provides the level. The Reality Engine measures the tolerance of that level.

| | **Jig** | **The Reality Engine** |
|---|---|---|
| Role | A level of description for AI work | Evidence that a level holds |
| Asks | Was *this* result made and checked to spec? | How often does *this way of working* stay within tolerance, and why does it fail? |
| Scope | One item, one run | Many runs, unseen cases |
| Means | Steps with contracts, code checks, complete records | Locked rules, sealed cases, statistics |
| Gives | A checked, recorded result | A trust report and a verdict on which version to rely on |

### 7.1 What the Reality Engine would measure

A step definition in Jig is a precise, versioned set of plain files. A script built from those steps is a
precise description of how a kind of work is done. That precision is exactly what a Reality Engine problem
pack needs:

| Reality Engine concept | For Jig work, for example a software factory |
|---|---|
| **Candidate** | A version of the way of working: a script plus its step definitions (prompts, constraints, checks), its fix-round limit and the model behind it |
| **Parts** (to take apart) | The `specify` prompt, the `build` prompt, the constraints, the number of fix rounds, the review criteria |
| **Test cases** | Requirement briefs never seen by whoever writes the candidates |
| **Scoring** | Hidden acceptance tests, run by Jig's no-AI `test` step after the build, and never shown to the building agent |
| **Tolerance** | For example, at least 95% of hidden acceptance tests pass and the app builds |
| **Sealed set** | Held-out briefs, opened once, for the final check |
| **Records** | Jig's store: every prompt, answer, check and test result, for scoring and audit |

The Reality Engine already lists two such uses for itself: measuring app-building agents by the hidden
acceptance tests their apps pass, and finding the specification format a coding model builds working
software from.

### 7.2 Quality at scale, as a loop

1. **Work at the higher level.** People describe and run AI work in Jig's vocabulary of requirements,
   steps, results and checks.
2. **Measure the level.** The Reality Engine runs the way of working on unseen cases and reports how often
   it stays within tolerance, why it fails, and which version is best.
3. **Rely on it, within the measured limits.** The verdict names a precise version, the files that won,
   with a known success rate, as a component carries a rating.
4. **Keep checking.** The Reality Engine's paper proposes small spot checks on fresh items after a full
   run. It notes that about 100 items catch a drop of 10 points, and about 400 a drop of 5. A Jig batch is
   a natural way to run them.

Each part alone is incomplete. A level of description without measurement is a convenient story of unknown
accuracy. Measurement without a clear level has nothing precise to measure. Together they make a claim no
demo can: *work done this way is within tolerance this often, on work it has not seen, for these
reasons.*

---

## 8. A worked example: the mini-games factory

The Jig repository includes a factory that builds three browser games from three requirement files:
Pong, a falling-block puzzle, and Snake. All three run at the same time, one process each:

```bash
py -m jig batch factory/games.yaml --script factory/game.jig --parallel 3 --continue-on-error
```

Each game goes through a spec, a build, the real tests, verification of every requirement against code and
test evidence, up to two fix rounds fed by exactly what verification found missing, and a code review. The
script calls `fail()` unless the tests pass and the computed verdict is "pass".

**Results of the first run (14 November 2026).** All three games completed in 5.5 minutes of wall time,
side by side, at a reported $2.50 of agent usage in total:

| Game | Requirements in the spec | Real tests | Verdict | Fix rounds | Time | Review findings |
|---|---|---|---|---|---|---|
| Pong | 11 (9 must-have) | 36 passed, 0 failed | pass, 11 of 11 satisfied | 0 | 329 s | 4 low |
| Falling-block puzzle | 13 (11 must-have) | 41 passed, 0 failed | pass, 13 of 13 satisfied | 0 | 320 s | 2 low |
| Snake | 10 (8 must-have) | 26 passed, 0 failed | pass, 10 of 10 satisfied | 0 | 244 s | 2 low, 1 informational |

Three details matter more than the green column:

- **The review found real defects that the tests and verification passed.** For example, in Pong a ball
  that has already passed a paddle can still be bounced back, and in Snake the key handler swallows
  browser shortcuts. Each finding is tied to a file and line that the code checks confirmed exist. A
  "pass" from one step is not the end of the story, which is the argument of section 5 in miniature.
- **The fix loop was not exercised.** Every game passed first time, so this run shows nothing about how
  well the fix rounds work. Only many runs, some of which fail, can show that.
- **Every claim is recorded.** The spec, every prompt, the agent's events, the test reports, the
  verification evidence and the review can be inspected for each game.

Three games are a demonstration, not a measurement. They show the higher level at work: three
requirement files in, three checked and recorded results out, with no prompt written by hand. They cannot
show how often the factory stays within tolerance on the next hundred briefs. That is a question for the
Reality Engine.

---

## 9. What we do not claim

- **The pairing is a proposal.** No Reality Engine problem pack for Jig work exists yet, and no Jig way
  of working has been measured. Section 7 describes a design, not a result.
- **Jig's checks are partial.** They catch fabricated files, functions, tests and sources, and they
  compute the verdict. They do not prove the quality of the work, and `verify` and `review` are still AI
  judgments.
- **One agent family.** Jig runs Claude Code today. Its step definitions are model-independent by design,
  but that has not been tested with other agents.
- **Boundaries have limits.** Jig's tool policies and its optional Docker sandbox reduce what an agent can
  do. Their known gaps are documented in Jig's [safety model](safety.md).
- **The Reality Engine's results are its own.** The figures in section 6 come from its first case study,
  with the limits that study states. They are not evidence about Jig.

---

## 10. Next steps

1. **A problem pack for Jig work.** Candidates are versions of a way of working; cases are briefs; scoring
   is hidden acceptance tests, run out of the building agent's sight.
2. **A set of briefs.** Write or generate enough briefs for every stage, with a sealed set held back.
3. **Measure the level itself.** Compare the game factory against a single prompt with no steps and no
   checks, on fresh briefs, to measure what working at the higher level is worth.
4. **Take it apart.** Test new `specify` and `build` prompts, fix-round limits and review criteria in
   combination, under the keep rule.
5. **Beyond software.** Apply the same pairing to other work: research memos, policy answers, contract
   reviews. The Reality Engine already lists policy, compliance and operations among its uses.

---

## References

- Jig: language, guide and examples. <https://github.com/runcor-ai/jig> · [The Jig guide](guide.md)
- The Reality Engine: method and site. <https://therealityengine.ca>
- The Reality Engine, how it works. <https://therealityengine.ca/how-it-works.html>
- *Describing Reality for AI*, white paper, final v0.1.0, run 5 (29–31 October 2026, updated
  1 November 2026). <https://therealityengine.ca/paper/>
- The Reality Engine, code. <https://github.com/LLMJester/reality-engine>
