# Commands

Every command is a plugin loaded by `jig/loader.py`, built-in or not. Run `jig commands` to see
what is loaded and from where, and `jig check` to validate every definition.

## Where commands come from

| Order | Directory | Source label |
|---|---|---|
| 1 | `jig/commands/` | builtin |
| 2 | `~/.jig/commands/` (or `$JIG_USER_COMMANDS`) | user |
| 3 | `<project>/commands/` | project |

A later definition with the same name replaces an earlier one, and `jig commands` shows `(overrides …)`.

## Files

```
<name>.yaml          definition (required)
<name>.md            prompt template (required for agent commands; or `prompt: other.md`)
<name>.schema.json   output JSON Schema (or `output_schema:` inline / `output_schema: file.json`)
```

## Definition fields

| Field | Default | Meaning |
|---|---|---|
| `purpose` | required | One line, shown by `jig commands` |
| `version` | `"0"` | Free-form |
| `target` | `{type: artifact_or_text, required: true}` | `text`, `artifact` (an existing id or bound variable), `artifact_or_text`, or `none`. For a script command, `as:` names the variable the target becomes (default `target`) |
| `parameters` | `{}` | `name: {type, default, enum?, items?, description}`. Types: `string`, `integer`, `number`, `boolean`, `list`, `object`, `path`. `max_attempts` and `approval_required` are reserved. |
| `artifact` | `optional` | `create` (the output creates a new artifact), `use` (target must be an artifact), `optional`, `none` |
| `requires` | `[]` | Stages of the artifact that must have completed, e.g. `[specify]` |
| `mode` | `agent` | `agent`, `procedure` (a built-in runner, currently `run_tests`), or `script` (another Jig script run as one step; see below) |
| `script` | | `mode: script` only: the `.jig` file, relative to the project (for built-in and user commands, to the command's directory) |
| `continue_on_error` | `false` | `mode: script` only: the inner script handles its own failed steps, as with `--continue-on-error` |
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
| `$build_spec` | The spec as a builder reads it: the FACTS notes when `specify` wrote them (`format="facts"`), otherwise the full spec |
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
| `facts_format` | With `format="facts"`: the FACTS notes have all five headings, are one-line bullets, and name every requirement id |

## Script commands: a script as one step

A whole Jig script can be used as one step of another. Its definition says which script, and what goes in
and comes out:

```yaml
# commands/make_game.yaml
purpose: Build one browser game from a requirements file, with tests, verify, fix rounds and review.
version: "1.0.0"
mode: script
script: factory/game.jig
target: {type: text, required: true, as: file}    # the target becomes the script's variable `file`
parameters:
  id: {type: string}                               # each parameter becomes a variable of the same name
continue_on_error: true                            # game.jig's fix loop handles failed checks itself
artifact: none
output_schema:
  type: object
  required: [id, tests, verdict, fixes, review]
```

- **In:** the target and the parameters become the script's variables. The loader checks that the script
  exists and parses, and that it uses no other outside variable.
- **Out:** whatever the script assigns to `result` is the step's output, checked against `output_schema`
  like any other command's answer. `make_game("pong.md", id="PONG-001")` then works in any script, with
  `r.output.verdict` and the rest.
- **Failure:** if the inner script fails (a failed step without `continue_on_error`, or `fail("...")`), the
  step fails with a `script_failed` finding naming the reason, and the output it set is kept.
- **Records:** the inner steps are recorded on their own artifacts as usual. The step's run folder has a
  `script.json` listing them, and the step's cost is the sum of theirs.
- **Re-running:** `--replace` and `--resume` on the outer script apply to the inner ones too. With
  `--resume`, a completed call is reused whole, and a failed one resumes inside, step by step.
- **Limits:** scripts can call scripts up to `script.max_depth` deep (default 3), so a script that calls
  itself stops. Calls run one after another; to build many items at the same time, use `jig batch`.

`factory/factory.jig` uses `make_game` to build three games in a few lines.

## Built-in commands

`specify`, `build`, `test`, `verify` and `research`. See their definitions in `jig/commands/`.
`review` in this repo's `commands/` is an example project command.
