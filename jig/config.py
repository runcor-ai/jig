"""Project configuration (jig.yaml) merged over built-in defaults."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

PKG_DIR = Path(__file__).resolve().parent

# Read-only commands Claude Code would otherwise auto-approve that reveal information about the
# host (identity, environment variables and secrets, processes, network). Deny always wins over
# allow. This is a best-effort list; the real isolation boundary is `--sandbox docker`.
INFO_LEAK_DENY = [f"Bash({c}:*)" for c in (
    "env", "printenv", "set", "export", "whoami", "id", "hostname", "uname", "ps", "top", "netstat", "ss",
    "ifconfig", "ipconfig", "ip", "arp", "route", "systeminfo", "tasklist", "wmic", "reg", "who", "w",
    "last", "history", "lsof", "df", "mount", "getent", "dscl", "scutil")]

DEFAULT_CONFIG: dict[str, Any] = {
    "store": ".jig",
    "workspace_root": "apps",
    "agent": {
        "adapter": "claude_code",
        "model": None,
        "effort": None,
        "timeout_s": 1200,
        "overrides": {},           # per-command overrides, e.g. build: {timeout_s: 7200}
    },
    # Tool boundaries, enforced by Claude Code (--tools / --allowedTools / --disallowedTools,
    # --permission-mode dontAsk, --setting-sources project). Commands name one of these, or
    # define their own inline. jig.yaml may override any of them.
    "tool_policies": {
        "none": {"tools": []},
        "read_workspace": {"tools": ["Read", "Grep", "Glob"], "deny": INFO_LEAK_DENY},
        "research": {"tools": ["WebSearch", "WebFetch"], "allow": ["WebSearch", "WebFetch"]},
        "write_workspace": {"tools": ["Read", "Grep", "Glob", "Write", "Edit"],
                            "allow": ["Write(./**)", "Edit(./**)"],
                            "deny": ["Write(./.claude/**)", "Edit(./.claude/**)"]},
        "build": {"tools": ["Read", "Grep", "Glob", "Write", "Edit", "Bash"],
                  "allow": ["Write(./**)", "Edit(./**)",
                            "Bash(npm:*)", "Bash(npx:*)", "Bash(node:*)",
                            "Bash(curl http://localhost:*)", "Bash(curl -s http://localhost:*)",
                            "Bash(curl -i http://localhost:*)",
                            "Bash(ls:*)", "Bash(mkdir:*)", "Bash(cat:*)", "Bash(sleep:*)"],
                  # docker is denied: `docker run -v /:/host` would escape the workspace.
                  "deny": ["Write(./.claude/**)", "Edit(./.claude/**)", "Bash(docker:*)",
                           "Bash(git push:*)", *INFO_LEAK_DENY]},
    },
    # Named agents a script can pick per step: build(spec, agent="luna"). A step without agent= uses `agent` above.
    "agents": {
        "opus": {"adapter": "claude_code", "model": "opus"},
        "sonnet": {"adapter": "claude_code", "model": "sonnet"},
        "luna": {"adapter": "codex", "model": "gpt-6-luna"},      # GPT-6 Luna through the Codex CLI
    },
    "retries": {"max_attempts": 2},
    "script": {
        "max_while_iterations": 10,   # a while loop whose condition is still true after this fails the script
        "max_steps": 100000,          # statements executed per run (stops runaway loops)
        "max_items": 100000,          # longest list/map/queue/set/string a script may build
    },
}


class ConfigError(ValueError):
    pass


def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_config(project_dir: Path) -> dict[str, Any]:
    cfg_path = Path(project_dir) / "jig.yaml"
    if cfg_path.exists():
        return deep_merge(DEFAULT_CONFIG, yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {})
    return copy.deepcopy(DEFAULT_CONFIG)
