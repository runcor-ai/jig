# Error codes

`jig errors` prints this list. Statuses: `blocked` = E_MISSING_CONTEXT, `unavailable` = E_UNAVAILABLE / E_AGENT_UNAVAILABLE, otherwise `failed`.

| Code | Meaning |
|---|---|
| E_PARSE | Script could not be parsed or uses disallowed syntax |
| E_SCRIPT | Script failed while running: type error, bad index, or a loop/size/step limit |
| E_UNKNOWN_COMMAND | Command is not loaded (see `jig commands`) |
| E_COMMAND_DEF | A command definition file is invalid |
| E_PARAM | Parameter missing, unknown, or of the wrong type |
| E_UNKNOWN_ARTIFACT | Referenced artifact does not exist |
| E_ARTIFACT_EXISTS | Script would create an artifact id that already exists (use --replace) |
| E_MISSING_CONTEXT | A stage this command requires has not completed |
| E_AGENT_UNAVAILABLE | The configured agent could not be started |
| E_AGENT_FAILED | The agent ran but did not return a usable result |
| E_SCHEMA | Agent output did not conform to the output schema |
| E_VALIDATION | Agent output failed semantic validation |
| E_TIMEOUT | Execution exceeded its time limit |
| E_BUDGET | Execution exceeded its cost budget |
| E_PROCEDURE | A runtime procedure (e.g. the test runner) failed |
| E_UNAVAILABLE | Capability or integration is not available in this environment |
