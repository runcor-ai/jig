# Commands

Every command is a plugin loaded by `lattice/loader.py`, built-in or not. Run `lattice commands` to see
what is loaded and from where, and `lattice check` to validate every definition.

## Where commands come from

| Order | Directory | Source label |
|---|---|---|
| 1 | `lattice/commands/` | builtin |
| 2 | `~/.lattice/commands/` (or `$LATTICE_USER_COMMANDS`) | user |
| 3 | `<project>/commands/` | project |

A later definition with the same name replaces an earlier one, and `lattice commands` shows `(overrides …)`.

## Files

```
<name>.yaml          definition (required)
<name>.md            prompt template (required for agent commands; or `prompt: other.md`)
<name>.schema.json   output JSON Schema (or `output_schema:` inline / `output_schema: file.json`)
```

## Definition fields

| Field | Default | Meaning |
|---|---|---|
| `purpose` | required | One line, shown by `lattice commands` |
| `version` | `"0"` | Free-form |
| `target` | `{type: artifact_or_text, required: true}` | `text`, `artifact` (an existing id or bound variable), `artifact_or_text`, or `none` |
| `parameters` | `{}` | `name: {type, default, enum?, items?, description}`. Types: `string`, `integer`, `number`, `boolean`, `list`, `object`, `path`. `max_attempts` and `approval_required` are reserved. |
| `artifact` | `optional` | `create` (the output creates a new artifact), `use` (target must be an artifact), `optional`, `none` |
| `requires` | `[]` | Stages of the artifact that must have completed, e.g. `[specify]` |
| `mode` | `agent` | `agent`, or `procedure` (a built-in runner, currently `run_tests`) |
| `tool_policy` | `none` | `none`, `read_workspace`, `write_workspace`, `research`, `build`, or inline `{tools, allow, deny}` |
| `validators` | `[]` | Built-in checks run after schema validation (see below) |
| `postprocess` | `[]` | `tests_must_pass`, `verify_verdict` |
| `idempotent` | `true` for agent commands | Retry once with the validation findings if the output fails |
| `timeout_s` | config default | Per agent call |

## Prompt placeholders

| Placeholder | Value |
|---|---|
| `$target` | The target text or artifact id |
| `$artifact_id` | The artifact id, or `(new)` |
| `$<param>` | Each parameter. Lists of strings render as bullets; `path` parameters render as the file's content (fence it in `<data>`). |
| `$parameters` | All parameters as JSON |
| `$spec` | The artifact's `specify` output |
| `$tests` | The artifact's recorded test results |
| `$expected_ids` | The requirement ids from the spec |
| `$context` | Every stage output of the artifact (only computed if used) |
| `$workspace_state` | What is already in the workspace |

## Built-in validators

| Name | Checks |
|---|---|
| `unique_ids` | No duplicate `id` values anywhere in the output |
| `constraints_reflected` | Every `constraints` parameter value is restated in `constraints_applied` |
| `claimed_files_exist` | `files_created` and `evidence_paths` exist in the workspace |
| `no_secrets_in_workspace` | No private keys or common API-token patterns |
| `all_criteria_assessed` | Every `criteria` parameter value appears in `criteria_assessed` |
| `findings_cite_existing_files` | Each finding's file exists and its line is within range |
| `tests_executed` | JUnit reports contained at least one test |
| `verify_covers_all_items` | One item per spec requirement |
| `evidence_files_exist`, `evidence_symbols_exist` | Cited files exist and the cited symbols occur in them |
| `test_evidence_matches_results` | Cited test names exist in the recorded test run |
| `research_findings_sourced`, `research_min_sources`, `research_sources_retrieved` | Every finding cites a listed source; enough sources; every URL appears in the session's own WebSearch/WebFetch log |

## Built-in commands

`specify`, `build`, `test`, `verify` and `research`. See their definitions in `lattice/commands/`.
`review` in this repo's `commands/` is an example project command.
