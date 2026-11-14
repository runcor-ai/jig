"""Loading of the project config (lattice.yaml) and the versioned registries."""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PKG_DIR = Path(__file__).resolve().parent
REGISTRY_DIR = PKG_DIR / "registry"
SCHEMA_DIR = PKG_DIR / "schemas"
PROMPT_DIR = PKG_DIR / "prompts"

DEFAULT_CONFIG: dict[str, Any] = {
    "store": ".lattice",
    "workspace_root": "apps",
    "agent": {
        "adapter": "claude_code",
        "model": None,
        "effort": None,
        "timeout_s": 1200,
        "overrides": {},           # per-command overrides, e.g. build: {timeout_s: 7200}
    },
    # Built-in tool boundaries, enforced by Claude Code (--tools / --allowedTools / --disallowedTools,
    # --permission-mode dontAsk, --setting-sources project). lattice.yaml may override any of them.
    "tool_policies": {
        "none": {"tools": []},
        "read_workspace": {"tools": ["Read", "Grep", "Glob"]},
        "research": {"tools": ["WebSearch", "WebFetch"], "allow": ["WebSearch", "WebFetch"]},
        "docs": {"tools": ["Read", "Grep", "Glob", "Write", "Edit"],
                 "allow": ["Write(./**)", "Edit(./**)"],
                 "deny": ["Write(./.claude/**)", "Edit(./.claude/**)"]},
        "build": {"tools": ["Read", "Grep", "Glob", "Write", "Edit", "Bash"],
                  "allow": ["Write(./**)", "Edit(./**)",
                            "Bash(docker compose:*)", "Bash(docker run:*)", "Bash(docker build:*)",
                            "Bash(docker ps:*)", "Bash(docker logs:*)", "Bash(docker images:*)",
                            "Bash(npm:*)", "Bash(npx:*)", "Bash(node:*)",
                            "Bash(curl http://localhost:*)", "Bash(curl -s http://localhost:*)",
                            "Bash(curl -i http://localhost:*)",
                            "Bash(ls:*)", "Bash(mkdir:*)", "Bash(cat:*)", "Bash(sleep:*)"],
                  "deny": ["Write(./.claude/**)", "Edit(./.claude/**)", "Bash(docker push:*)",
                           "Bash(docker login:*)", "Bash(git push:*)", "Bash(rm -rf /:*)"]},
    },
    "retries": {"max_attempts": 2},
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


@dataclass
class Registry:
    version: str
    commands: dict[str, dict]
    profiles: dict[str, dict]
    stacks: dict[str, dict]
    decision_models: dict[str, dict]
    schemas: dict[str, dict] = field(default_factory=dict)

    def schema(self, name: str) -> dict:
        if name not in self.schemas:
            path = SCHEMA_DIR / f"{name}.json"
            if not path.exists():
                raise ConfigError(f"output schema '{name}' not found at {path}")
            self.schemas[name] = json.loads(path.read_text(encoding="utf-8"))
        return self.schemas[name]


REQUIRED_COMMAND_FIELDS = ["category", "purpose", "maturity", "target", "parameters", "artifact", "requires",
                           "output_schema", "execution", "validators", "idempotent", "controls", "errors"]
CATEGORIES = {"definition", "investigation", "decision", "design", "execution", "quality", "delivery", "control"}


def load_registry(registry_dir: Path = REGISTRY_DIR) -> Registry:
    cmds = yaml.safe_load((registry_dir / "commands.yaml").read_text(encoding="utf-8"))
    profs = yaml.safe_load((registry_dir / "profiles.yaml").read_text(encoding="utf-8"))
    dms = yaml.safe_load((registry_dir / "decision_models.yaml").read_text(encoding="utf-8"))
    reg = Registry(version=str(cmds["version"]), commands=cmds["commands"], profiles=profs.get("profiles", {}),
                   stacks=profs.get("stacks", {}), decision_models=dms.get("models", {}))
    _check_registry(reg)
    return reg


def _check_registry(reg: Registry) -> None:
    from . import validators  # local import to avoid cycle
    problems = []
    for name, spec in reg.commands.items():
        for f in REQUIRED_COMMAND_FIELDS:
            if f not in spec:
                problems.append(f"{name}: missing field '{f}'")
        if spec.get("category") not in CATEGORIES:
            problems.append(f"{name}: bad category {spec.get('category')!r}")
        if not (SCHEMA_DIR / f"{spec.get('output_schema')}.json").exists():
            problems.append(f"{name}: output schema '{spec.get('output_schema')}' missing")
        for v in spec.get("validators", []):
            if v not in validators.VALIDATORS:
                problems.append(f"{name}: unknown validator '{v}'")
        if spec.get("execution", {}).get("mode") not in {"agent", "procedure", "native"}:
            problems.append(f"{name}: bad execution mode")
    if problems:
        raise ConfigError("invalid command registry:\n  " + "\n  ".join(problems))


def load_config(project_dir: Path) -> dict[str, Any]:
    cfg_path = project_dir / "lattice.yaml"
    cfg = DEFAULT_CONFIG
    if cfg_path.exists():
        cfg = deep_merge(DEFAULT_CONFIG, yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {})
    return cfg
