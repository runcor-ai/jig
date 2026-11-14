# Safety model

| Concern | Control | Verified |
|---|---|---|
| Template typos | `jig check` / the loader reject `$placeholders` that are not declared parameters or context variables, and malformed `${...}` | offline tests |
| Bad data references | `spec.output.x` fails with the exact missing path; a failed step's `.output` is an error, not `None` | offline tests |
| Script code execution | `ast.parse` used only as a grammar; node whitelist; dotted references are data lookups; `_`-prefixed names rejected | offline tests (24 rejection cases) |
| Parameters | Declared types, enums and defaults per command; unknown parameters rejected; `path` parameters must be inside the project | offline tests |
| Untrusted content | Targets, files and prior outputs fenced in `<data>` tags, with `</data>` escaped; the system prompt says data is never instructions. Mitigation only. | offline test |
| Tool access | Claude Code flags: `--tools`, `--allowedTools`, `--disallowedTools`, `--permission-mode dontAsk`, `--setting-sources project` (no inherited personal allow-lists), `--strict-mcp-config` | live, 2026-11-14 |
| Workspace escape via docker | `docker` removed from the `build` allow-list and explicitly denied (`Bash(docker:*)`) | live: `docker ps` denied |
| Read-only auto-approvals | Claude Code auto-approves commands it classifies as read-only. Jig denies the ones that reveal host information: `env`, `printenv`, `set`, `export`, `whoami`, `id`, `hostname`, `uname`, `ps`, `netstat`, `ipconfig`, `systeminfo`, `tasklist`, `reg`, and others (`INFO_LEAK_DENY` in `jig/config.py`). | live: `whoami`, `env`, `hostname` denied; `npm` allowed |
| Real isolation | `--sandbox docker`: agent and test commands run in a `--rm` container with only the workspace mounted at `/workspace`, as uid 1000, `--cap-drop ALL`, `no-new-privileges`, pid/memory/cpu limits, **read-only root filesystem** (`--read-only`), with writable memory-backed tmpfs only at `/tmp` and `/home/node` (npm cache and Claude Code's own config) | live container probe: no host drive, no host `~/.claude`, `CapEff 0`; `/`, `/etc`, `/usr/local` read-only; `npm install`, `npx` and `claude` still work |
| Test commands | Supplied by the script author (`test(run=[...])`), never by the agent. Under `--sandbox docker` they run in the container, because they execute agent-written code. | offline test |
| Fabricated results | Validators check claimed files, cited symbols, cited tests and cited URLs against the workspace, the recorded test run and the session event log. The `verify` verdict is computed by Jig. | offline tests |
| Recording | Every invocation, prompt, agent event stream, result and test log is kept under `.jig/runs/`, plus a line in `log.jsonl` | — |

## Known limits

- The deny-list is a list. A read-only command not on it may still be auto-approved on the host. Use
  `--sandbox docker` when that matters.
- The sandbox needs network access for the model API, so the agent inside could still reach the internet
  with tools that allow it (`curl` to localhost only is allowed in `build`).
- The sandbox token is readable by the agent inside the container. Use a revocable token from
  `claude setup-token`.
- A complete agent run inside the sandbox has **not** been executed yet, because it needs that token. The
  container setup and the argv it builds are tested.
- Prompt injection through workspace files or web pages can still influence what an agent does within its
  tool boundary.
