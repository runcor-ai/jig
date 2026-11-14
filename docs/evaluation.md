# Evaluation layer

Every command result carries `validation` from three layers:

1. **JSON schema**: `lattice/schemas/<schema>.json`. It is also passed to Claude Code as `--json-schema`
   (without the `$schema` key, which the CLI does not resolve).
2. **Semantic validators**: `lattice/validators.py`, listed per command in the registry. Examples:
   - `profile_controls_reflected`: every enabled profile control has an NFR with `source: profile:<path>`.
   - `design_traces_all_requirements`, `design_resolves_open_decisions`.
   - `stack_contract_files_exist`, `compose_services_present`, `migrations_present` (filesystem).
   - `findings_cite_existing_files`: review findings point at real files and in-range lines.
   - `evidence_symbols_exist`: verify evidence symbols literally occur in the cited file.
   - `test_evidence_matches_results`: cited tests exist in the recorded JUnit results.
3. **Deterministic post-processing**:
   - `test` fails if any suite fails or produces no reports.
   - `verify` computes its verdict itself from the per-item statuses, must-priority requirements,
     acceptance criteria and the recorded test run. The agent never declares the verdict.

Error-severity findings make the command `failed`; warnings are reported but do not fail it. For
idempotent commands, error findings trigger one re-prompt that includes the findings.

`lattice exec 'validate("CRM-001")'` re-runs layers 1 and 2 on stored stages against the current
workspace, for example after manual edits.

## Benchmark harness

```bash
lattice bench bench/suites/crm_requirements.yaml --runs 3 --mode baseline lattice
```

- **baseline**: a direct `claude -p` call with a reasonable natural-language prompt. No schema, profile or
  validators.
- **lattice**: the `requirement()` command with the enterprise profile and stack, in an isolated
  temporary store.

Both modes are scored by the same rules from the suite file:

| Metric | How it is scored |
|---|---|
| Schema compliance | Output validates against the schema |
| Requirement coverage | Share of the spec's FR-01..FR-09 matched by keyword in the functional requirements |
| Constraint adherence | Stack and profile terms present |
| Task success | All of the above meet their thresholds |
| Consistency | Mean pairwise Jaccard similarity of covered items across runs, plus FR count stdev |
| Time, tokens and cost | As reported by Claude Code |
| Failure categories | `no_parseable_output`, `schema`, `coverage`, `constraints`, or an agent error code |

Results, including raw outputs, the suite and the agent config, are written to `bench/results/*.json` so
comparisons can be reproduced and re-scored. Keyword coverage is a coarse proxy and is documented as
such.
