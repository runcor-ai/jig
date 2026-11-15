# Jig architecture: what the code enforces

This document describes what Jig actually enforces, where the deterministic boundaries are, and where they are
not. Every claim cites the code. It is the reference for the README and the pilot study; where they say more than
this, this wins.

## 0. The thesis, mapped to the code

> AI work cannot scale while the way of working is buried in the plumbing. It needs a dedicated layer of
> abstraction that lifts the definition of the work above the mechanics of executing it, checks every claim before
> it is used, and treats measurement at scale as a property of the layer rather than an afterthought. The layer
> is a control plane, not an orchestrator: it governs what work is permitted, what counts as verified evidence, and
> how reliable a way of working is shown to be, whoever does each step.

| Thesis claim | What the code does | Holds? |
|---|---|---|
| **The unit of work is defined above the prompt** | The unit is a step: one command call under a contract, on an artifact (section 1). A script names steps, inputs and agents; it never contains a prompt or a tool permission | Yes |
| **Mechanics are abstracted** | Encapsulated in the command definition, one level down: the prompt template (`*.md`), the tool policy, the output JSON Schema, the validators and post-processors, the retry rule, the timeout, the `requires` stages (`jig/loader.py`, `jig/commands/`). Encapsulated in the runtime: agent invocation and flags (`jig/adapters/`), event parsing, cost capture, context injection, artifact storage, the step journal, batch processes, ports and locks | Yes |
| **Definition is decoupled from execution** | The same script runs with a different agent per step (`agent="opus"` / `"luna"`, two adapters), under `--sandbox docker`, as one run or a parallel batch, and resumes with `--resume`. Changing a prompt, a check or a model changes no script | Yes, for two agent hosts |
| **A control plane, whoever does the step** | The script names each step's worker. Models through two adapters, chosen per step with `agent=` (`jig/adapters/`, `runtime.agent_for`); deterministic code as a procedure with no model (`test`, `jig/procedures.py`); a whole script as one step (`mode: script`, `runtime._run_script_step`, `_execute_each`). The contract, checks and record are the same for each. Human experts as a worker (`agent="experts"`) are a design only (`docs/design/expert-agents.md`) | Yes for models, code and sub-scripts; **not built** for human experts. The shipped checks suit building and research; other work needs new contracts and checks |
| **Claims are checked, not trusted** | Schema validation, evidence validators, a model-free `test` procedure and a computed verdict (sections 1–2) | For evidence and consistency, not meaning (section 2) |
| **Measurement is built in** | Every way of working is plain, versionable files (a script plus command definitions with a `version` field). Every step writes the same structured record under `.jig/runs/`: inputs, prompt, agent events, validated output, findings, cost. `jig batch` runs one script over many items with a per-item summary | **In part.** The layer makes ways of working measurable: a precise unit, uniform records, repeatable runs. It does not compute ratings, ranges or significance; those come from an external instrument (in the pilot study, The Reality Engine) |

## 1. The mechanism

### The unit of abstraction: a contracted step on an artifact

The unit is not the script and not the prompt. It is **one command call, executed under a contract, against an
artifact**:

| Part | What it is | Where |
|---|---|---|
| Command contract | A plugin definition: typed target and parameters, a tool policy, an output JSON Schema, a list of validators and post-processors, a prompt template, an idempotency flag, a timeout, and the stages it `requires` | `jig/loader.py`, `jig/commands/*.yaml` |
| Artifact | A persistent record: a manifest, an append-only output file per stage run, a history, a workspace folder | `jig/store.py` |
| Adapter | Who executes an agent step: Claude Code or Codex (or a fixture in tests) | `jig/adapters/` |
| Procedure | A step with no model at all (`test`: runs commands, parses JUnit) | `jig/procedures.py` |
| Script | A restricted program that composes steps: plain logic runs locally; only command calls reach an agent | `jig/parser.py`, `jig/script.py` |
| Script command | A whole script used as one step (`mode: script`): its target and parameters become its variables, what it assigns to `result` is the step's output, checked against the command's schema; its steps are recorded on their own artifacts and listed in the step's `script.json`; `--replace` / `--resume` pass through; nesting is capped by `script.max_depth` (default 3). `each=[...]`, `parallel=N` runs it for every item at once, one `jig run` process per item, and binds the results as a list in order | `jig/loader.py` (`_check_scripts`), `jig/runtime.py` (`_run_script_step`, `_execute_each`) |

### How the concerns are separated

| Concern | Mechanism | Deterministic? |
|---|---|---|
| **Intent** | The step's target text plus parameters, validated against declared types; a `brief` file is read as untrusted data, fenced in `<data>` with `</data>` escaped and capped in size | Yes: parameter validation, fencing (`runtime._validate_params`, `read_untrusted`) |
| **Context** | Prior results of the same artifact injected by named placeholders (`$spec`, `$build_spec`, `$tests`, `$expected_ids`, `$workspace_state`; `$context` = all stage outputs, truncated at 120,000 characters). Prerequisites enforced: a step whose `requires` stages have not completed fails with `E_MISSING_CONTEXT` | Yes: which context a step sees is fixed by its template |
| **Execution** | The adapter runs the agent with the step's tool policy. Claude Code: `--tools`, `--allowedTools`, `--disallowedTools`, `--permission-mode dontAsk`, no inherited settings or MCP. Codex: a read-only or workspace-write sandbox, web search off | The boundary is enforced by the agent host, not by Jig itself; see section 2 |
| **Verification** | (1) the answer must match the JSON Schema; (2) named validators check claims against the workspace and records; (3) post-processors (`tests_must_pass`, `verify_verdict`) turn facts into pass/fail; (4) a failed check gets one retry with the findings, if the command is idempotent | The checks are deterministic code; what they check is consistency and evidence, not meaning |
| **Control** | The script interpreter: whitelisted syntax only (no imports, functions or attribute access), capped `while` loops, step and size limits, a failed step stops the script unless `--continue-on-error` | Yes |
| **Record** | Every invocation, prompt, agent event stream, output, validation finding and cost under `.jig/runs/`; a step journal per script for `--resume` | Yes |

### The deterministic checks that exist

`unique_ids`, `constraints_reflected`, `facts_format`, `claimed_files_exist`, `no_secrets_in_workspace`,
`all_criteria_assessed`, `findings_cite_existing_files`, `tests_executed`, `verify_covers_all_items`,
`evidence_files_exist`, `evidence_symbols_exist`, `test_evidence_matches_results`, `research_findings_sourced`,
`research_min_sources`, `research_sources_retrieved` (`jig/validators.py`), plus the procedure `run_tests` and the
post-processors `tests_must_pass` and `verify_verdict` (`jig/procedures.py`).

## 2. Gaps between the current framing and the code

| The framing says or implies | The code actually does | Consequence |
|---|---|---|
| "Every answer is checked by code" | Every answer is checked for **format and evidence consistency**: files exist, cited functions occur in the cited file, cited tests ran, cited URLs were retrieved. No check judges whether code is correct or a claim is true | Fabrication is caught; a wrong but well-evidenced answer is not. Correctness comes only from tests the script author supplies (`test`) or, in the experiments, hidden tests outside Jig |
| "The verdict is computed by code" | `compute_verdict` is deterministic, but its inputs are the `verify` agent's per-requirement statuses plus the recorded test result | The verdict is a rule applied to an AI judgment plus a fact, not an independent verification |
| "Each step can only use its allowed tools" | Enforced by Claude Code's flags; a deny-list of information commands, not an allow-everything-safe guarantee. With Codex, `build` runs in a workspace-write sandbox where any command is allowed inside the folder | The boundary is as strong as the agent host. Real isolation (`--sandbox docker`) exists, but a full agent run inside it has not been executed |
| "A level of description" for "AI work" in general | Most validators and the built-in commands are shaped for building and researching (`specify`, `build`, `test`, `verify`, `research`) | The abstraction is general, but the shipped evidence checks are domain-specific; new domains need new validators to get the same guarantees |
| "Model-independent" | Two adapters (Claude Code, Codex) plus a test fixture | Independence is designed in, demonstrated for two hosts |
| "Retries with feedback" | One retry on validation failure, only for idempotent commands; `build` is not retried automatically | Repair of a build happens through the script's own fix rounds, not the runtime |
| "Everything is recorded" | True for every step. The artifact keeps the latest output per stage in its manifest and every output on disk | `$spec` and `$context` read the latest output of each stage |
| Experts as agents | Design only (`docs/design/expert-agents.md`) | Not built |
| "A way of working becomes a step at the level above" | A script command runs a whole script as one step and returns its checked `result`; `each=` runs it for many items in parallel processes (`factory/factory.jig` over `make_game`) | Composition and parallel calls are built for script commands; `each=` does not yet apply to agent commands. `make_game` is tested offline and was run live on 14 Nov 2026: once alone (PONG-002: 35 tests passed, verify pass, 5 minutes, $0.81), then for three games in parallel through `factory/factory.jig` (PONG-003, TETRIS-002, SNAKE-002: all passed tests and verify with no fix rounds; 48, 31 and 21 tests; 5.0 minutes in all, $1.99) |

## 3. Three sharper framings

Each is built on the actual boundary in the code: deterministic contracts and evidence checks around
nondeterministic agent steps.

### Option A: the boundary

**Title:** Contracted Steps: Deterministic Boundaries Around Nondeterministic Agents
**Subtitle:** A step-level contract layer for agent work, and a measurement of how far it can be trusted

**Thesis.** An agent asked to do a task returns a claim of success that nothing outside the agent checks, with tools
nothing outside it limits. Jig makes each step of agent work a contract: the host restricts the step's tools, the
answer must match a schema, and deterministic checks test its claims against the workspace and the recorded test
run before a script may use it. The Reality Engine then measures, on sealed cases, how often a script built from
such steps is right and which of its steps that depends on.

### Option B: the failure mode

**Title:** Claims Are Not Results: Enforcing Evidence at Every Agent Step
**Subtitle:** How a contract layer catches fabricated success, and what it cannot catch

**Thesis.** The characteristic failure of unstructured agent work is a confident report ("all tests pass, every
requirement done") that is unchecked and sometimes untrue. Jig refuses to pass a step's result on until its cited
files, functions, tests and sources are confirmed against the workspace and the recorded runs, and it computes the
final verdict from those facts. This catches fabrication and missing evidence; it does not judge meaning, so
correctness still rests on tests, and the Reality Engine measures how often the whole pipeline is right.

### Option C: the layer

**Title:** Steps, Not Prompts: A Contract Layer for Agent Work
**Subtitle:** Separating intent, context, execution and verification, and measuring the result

**Thesis.** Prompting mixes what is wanted, what the model sees, what it may do and how its answer is judged into
one string, so none of them can be controlled or audited separately. Jig separates them: typed intent, context
injected only from recorded results, execution under a host-enforced tool policy, and verification by schema and
evidence checks, composed by a restricted script whose every agent call is a visible line. The Reality Engine rates
the resulting way of working on sealed cases, with its failure modes and its uncertainty.

**Decision (14 Nov 2026):** keep the title **Abstraction for AI Work**. The paper is a thought paper with a short
experiment: the thinking behind working with AI at scale, from generating work to measuring it, because the way
of working can no longer stay buried in the plumbing.

- **Subtitle:** Why AI work cannot scale while the way of working is buried in the plumbing, and what a layer of
  abstraction must separate, check and measure.
- **Thesis statement:** The machinery for AI work is now strong: orchestration frameworks, agent teams, and harnesses with deterministic
  hooks. What is missing is a level above it. The way of working is spread across prompts in code, tool rules in
  configs, checks in hook scripts and coordination in agent messages, so it is hard to read as a whole, every
  change touches the plumbing, success is often the agent's own report, and the process is rarely a unit precise
  enough to be compared, repeated or measured. To happen reliably at scale, AI work needs a dedicated layer of
  abstraction that lifts the definition of the work above the mechanics of executing it, checks every claim before
  it is used, and makes measurement at scale a property of the layer: only a precise, versioned definition of a
  way of working can be run on many cases, compared, taken apart and rated.

**Version 0.5 (15 Nov 2026):** the paper frames the layer as a **control plane, not an orchestrator**:
orchestration frameworks manage how agents run and coordinate; this layer governs what work is permitted, what
counts as verified evidence, and how reliable a way of working is shown to be, whoever does each step (a frontier
or small model, deterministic code, a sub-script, or, planned, human experts). Section 03 adds a non-code example,
a regulatory review, stated as a design: only `research` and its source checks ship today.

## 4. Where Jig sits

Descriptions of other approaches are of their general design, at the level of their public documentation; each is
broader than one row can show. The last row lists only what Jig's code implements (sections 0–2).

| Framework / Approach | Abstraction Layer (vs. Raw Scripts) | Deterministic Boundary | Context & State Isolation | Measurement & Eval at Scale | Primary Bottleneck Addressed |
|---|---|---|---|---|---|
| Raw Prompting / Ad-hoc Scripts | None: the prompt and the plumbing are the work | None beyond whatever the script parses | Conversation history or script variables, managed by hand | Manual: demos and spot checks | Getting a capable model to do a task at all |
| DSPy | Modules with typed signatures, composed in Python | Typed input and output fields | Program variables | Built in for optimisation: prompts compiled against a metric on an evaluation set | Brittle, hand-written prompts in multi-step programs |
| LangGraph / Agent Frameworks | Nodes and edges of a stateful graph, in code | Code-defined control flow and a state schema | Shared graph state, checkpointed and persisted | Not part of the graph; tracing and evaluation are separate tools | Durable, resumable, long-running agent control flow |
| MCP | A protocol for tools, resources and prompts served to a model | A JSON Schema for each tool's input | Resources fetched by the host for the model | Not in scope | Connecting many tools and data sources to many models |
| Skills / Procedural SOPs | Packaged instructions, sometimes with scripts, loaded into context | Little beyond bundled scripts: the model follows the guidance | Loaded into the model's context on demand | Not built in | Missing or inconsistent know-how and procedure |
| **Abstraction for AI Work (Jig)** | **A restricted script of contracted steps; prompts, tool policies, output schemas and checks live one level down in command definitions** | **Per step: tool policy enforced by the agent host; output JSON Schema; deterministic evidence validators; a model-free `test` procedure; computed verdict. Per script: whitelisted syntax, loop, step and size limits** | **A persistent artifact per item (manifest, append-only stage outputs, own workspace); context injected only from named, recorded results; untrusted inputs fenced; each batch item in its own process, folder and ports** | **Every way of working is versioned files; every step writes a uniform record (output, findings, cost) under `.jig/runs/`; `jig batch` runs a script over many items in parallel with per-item summaries. Ratings and ranges are external (The Reality Engine)** | **Unverified self-reported agent success, unbounded tool use, and work that cannot be compared, audited or measured** |

## 5. The opening narrative (applied in README.md and the paper)

> The machinery for AI work is now strong: orchestration frameworks, agent teams, and harnesses with deterministic
> hooks. What is missing is a level above it. The way of working is spread across prompts in code, tool rules in
> configs, checks in hook scripts and coordination in agent messages, so it is hard to read as a whole, every
> change touches the plumbing, success is often the agent's own report, and the process is rarely a unit precise
> enough to be compared, repeated or measured.
>
> Jig moves the work up a level. The script defines the work: which steps, in what order, with which inputs and
> which agent, and what to do when a check fails. Each step's mechanics (its prompt, tools, answer format and checks)
> are written once, one level down, and the runtime executes them on whichever agent host the script names. Because
> a way of working is now a precise, versioned definition that leaves the same record on every run, it can be run
> on many cases, compared with another, taken apart and rated.
>
> It is a control plane, not an orchestrator: orchestration frameworks manage how agents run and coordinate; Jig
> governs what work is permitted, what counts as verified evidence, and how reliable a way of working is shown to
> be, whoever does each step: a model, deterministic code, another Jig script, or (planned) human experts.
