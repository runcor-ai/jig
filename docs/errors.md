# Error codes

`lattice errors` prints this list. Every failed result carries `error.code`.

| Code | Status | Meaning |
|---|---|---|
| E_PARSE | failed | Script could not be parsed, or uses disallowed syntax. Nothing is executed. |
| E_UNKNOWN_COMMAND | failed | Command is not in the registry |
| E_PARAM | failed | Parameter missing, unknown, wrong type, bad enum, or path outside the project |
| E_PROFILE | failed | Unknown profile or stack, version pin mismatch, or bad override |
| E_UNKNOWN_ARTIFACT | failed | Referenced artifact does not exist |
| E_ARTIFACT_EXISTS | failed | Script would re-create an existing id (use `--replace`) |
| E_MISSING_CONTEXT | blocked | A required stage has not run or did not complete |
| E_APPROVAL_REQUIRED | awaiting_approval | Gated command without an unused approval |
| E_DECISION_MODEL | failed | Unknown decision model |
| E_AGENT_UNAVAILABLE | unavailable | Agent CLI missing or not startable |
| E_AGENT_FAILED | failed | Agent ran but returned no usable result |
| E_SCHEMA | failed | Output violates the JSON schema |
| E_VALIDATION | failed | Output fails a semantic validator (see `validation.findings`) |
| E_TIMEOUT | failed | Exceeded `timeout_s` |
| E_BUDGET | failed | Exceeded `max_budget_usd` |
| E_PROCEDURE | failed | Runtime procedure error |
| E_UNAVAILABLE | unavailable | Capability or integration not available (docker down, `deploy`) |
