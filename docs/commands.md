# Command library

The authoritative definition is `lattice/registry/commands.yaml` (v0.1.0). `lattice commands` prints it,
and `lattice commands --json` dumps it.

Every entry defines: `category`, `purpose`, `maturity`, `target`, `parameters` (type, default, enum),
`artifact` (create/use/optional/none), `requires` (required context: prior stages), `output_schema`,
`execution` (mode and tool policy), `validators`, `idempotent` (retry safety), `controls`
(approval_required) and `errors`.

## Maturity levels

| Maturity | Meaning | Commands |
|---|---|---|
| core | Dedicated prompt, schema and validators; exercised end to end | requirement, design, build, test, review, verify |
| generic | Shared agent path (`generic_analysis`, `decision` or `build` schema) with shared validators | scope, specify, constrain, research, analyze, compare, extract, decide, evaluate, challenge, justify, architect, model, prototype, implement, refactor, integrate, document |
| native | Implemented by the runtime; no agent | validate, report, package, approve, checkpoint, rollback, status |
| unavailable | Defined and gated; returns `E_UNAVAILABLE` | deploy |

## Core commands

| Command | Requires | Tools | What is checked |
|---|---|---|---|
| `requirement(goal, stack=[], standard=None, brief=None, overrides={}, id=None)` | none | none | unique ids; ACs reference real FRs; every enabled profile control → NFR; every stack component → constraint |
| `design(ID, decision_model=None, notes=None)` | requirement | none | every FR traced; every open decision resolved; layout includes contract paths; endpoints reference real FRs |
| `build(ID, path=None, budget_usd=None, notes=None)` | requirement, design | build (workspace) | contract files exist; compose services present; migrations exist; claimed files exist; no committed secrets |
| `test(ID, suites=[], diagnose=False)` | build | the runner itself (docker) | suites from the stack profile are executed and JUnit XML / HTTP checks parsed; fails if anything fails or no reports exist |
| `review(ID, criteria=[...])` | build | read_workspace | every criterion assessed; every finding cites an existing file and an in-range line |
| `verify(ID, against="requirements")` | requirement, build | read_workspace | every FR and AC covered; evidence files and symbols exist; cited tests exist in recorded results; verdict computed deterministically |

## Profiles

`lattice/registry/profiles.yaml` holds the quality profiles (`enterprise`, `prototype`) and stacks
(`java_react_postgres`). Each is versioned. A script can pin a version (`standard="enterprise@1.0.0"`) and
override a leaf (`overrides={"security.audit_logging": False}`). The resolved profile and stack are stored
in the artifact manifest, so later stages use exactly what `requirement` used.

The stack's `contract` (required paths, compose services, ports and rules) is what lets `test` run the
application without trusting the build agent's account of it.

## Decision models

`lattice/registry/decision_models.yaml` defines 7 models: architecture_selection, technology_selection,
risk_assessment, trade_off_analysis, root_cause_analysis, evidence_verification and
reversibility_assessment. Each lists inputs, criteria, assumptions, outputs and rules.

A model is used only when a command names it (`decide(..., decision_model="risk_assessment")`, or
`design(ID, decision_model=...)`). The runtime injects it into the prompt, and `decision_model_complete`
checks that every option is scored against every criterion. No second LLM call is made.

## Adding a command

Add a registry entry. If it needs a new output shape, add a schema, optionally a prompt template
`prompts/<name>.md`, and any validators (decorated with `@validator`). There is no per-command code path in
the runtime. Registry loading fails fast on missing fields, unknown validators or missing schemas.
