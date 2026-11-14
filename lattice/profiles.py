"""Profile and stack resolution with version pinning and explicit overrides."""
from __future__ import annotations

import copy
from typing import Any

from .config import Registry


class ProfileError(ValueError):
    code = "E_PROFILE"


def _norm(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def resolve_profile(reg: Registry, standard: str | None, overrides: dict[str, Any] | None = None) -> dict | None:
    if not standard:
        if overrides:
            raise ProfileError("overrides given without a standard profile")
        return None
    name, _, pin = standard.partition("@")
    if name not in reg.profiles:
        raise ProfileError(f"unknown profile '{name}'. Available: {', '.join(sorted(reg.profiles))}")
    prof = copy.deepcopy(reg.profiles[name])
    if pin and str(prof.get("version")) != pin:
        raise ProfileError(f"profile '{name}' is version {prof.get('version')}, script pins {pin}")
    applied = {}
    for dotted, value in (overrides or {}).items():
        parts = dotted.split(".")
        node = prof
        for p in parts[:-1]:
            if not isinstance(node.get(p), dict):
                raise ProfileError(f"override '{dotted}' does not match the profile structure")
            node = node[p]
        if parts[-1] not in node:
            raise ProfileError(f"override '{dotted}' names an unknown setting")
        if isinstance(node[parts[-1]], dict):
            raise ProfileError(f"override '{dotted}' must target a leaf setting")
        node[parts[-1]] = value
        applied[dotted] = value
    return {"name": name, "version": str(prof.pop("version", "")), "description": prof.pop("description", ""),
            "overrides": applied, "settings": prof}


def resolve_stack(reg: Registry, stack: list[str]) -> dict | None:
    if not stack:
        return None
    wanted = {_norm(s) for s in stack}
    matches = []
    for sid, s in reg.stacks.items():
        options = [s.get("match", [])] + list(s.get("also_matches", []))
        if any(opt and {_norm(m) for m in opt} == wanted for opt in options):
            matches.append(sid)
    if not matches:
        known = "; ".join(f"{k}={v.get('match')}" for k, v in reg.stacks.items())
        raise ProfileError(f"no stack profile matches {stack}. Known stacks: {known}")
    sid = matches[0]
    s = copy.deepcopy(reg.stacks[sid])
    s.pop("also_matches", None)
    return {"name": sid, "version": str(s.pop("version", "")), **s}


def enabled_controls(profile: dict | None) -> list[str]:
    """Dotted paths of every boolean setting that is true, e.g. security.audit_logging."""
    out: list[str] = []

    def walk(node: Any, prefix: str):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{prefix}.{k}" if prefix else k)
        elif node is True:
            out.append(prefix)

    if profile:
        walk(profile["settings"], "")
    return out


def stack_terms(stack: dict | None) -> list[str]:
    if not stack:
        return []
    terms = []
    for layer in ("backend", "frontend", "database"):
        for key in ("language", "framework", "engine"):
            v = (stack.get(layer) or {}).get(key)
            if v and v not in terms:
                terms.append(v)
    return terms
