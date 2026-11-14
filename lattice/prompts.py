"""Prompt rendering for any command. Templates use $placeholders:

    $command $artifact_id $target $parameters      always available
    $<param>                                       every parameter of the command
                                                   (lists of strings -> bullet lines; path params -> file content)
    $spec $tests $expected_ids                     from the artifact's specify / test stages
    $context                                       all stage outputs of the artifact (JSON)
    $workspace_state                               what is in the workspace already
"""
from __future__ import annotations

import json
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING

from .validators import requirement_ids

if TYPE_CHECKING:
    from .runtime import ExecContext, Runtime

SYSTEM_PROMPT = Path(__file__).resolve().parent / "system_prompt.md"
MAX_CONTEXT_CHARS = 120_000


def _j(obj) -> str:
    return json.dumps(obj, indent=1, ensure_ascii=False) if obj is not None else "none"


def _value(rt: "Runtime", ps: dict, v) -> str:
    if v is None:
        return "none"
    if ps.get("type") == "path":
        return rt.read_untrusted(v)
    if isinstance(v, list) and all(isinstance(x, str) for x in v):
        return "\n".join(f"- {x}" for x in v) if v else "none"
    if isinstance(v, (dict, list)):
        return _j(v)
    return str(v)


def tests_summary(test: dict | None) -> str:
    if not test:
        return "No test results have been recorded for this artifact."
    return _j({"passed": test.get("passed"), "totals": test.get("totals"),
               "case_names": test.get("case_names", []), "failed_cases": test.get("failed_cases", [])})


def workspace_state(ctx: "ExecContext") -> str:
    ws = ctx.workspace
    if not ws or not ws.exists() or not any(ws.iterdir()):
        return "empty (start from scratch)."
    entries = sorted(p.name + ("/" if p.is_dir() else "") for p in ws.iterdir())
    return ("NOT empty; top-level entries: " + ", ".join(entries) +
            ". Inspect it and continue or repair the existing implementation rather than starting over.")


def artifact_context(rt: "Runtime", ctx: "ExecContext") -> str:
    if not ctx.artifact_id:
        return "none"
    parts = {s: rt.store.stage_output(ctx.artifact_id, s) for s in ctx.manifest.get("stages", {})}
    text = _j(parts)
    return text[:MAX_CONTEXT_CHARS] + ("\n...[truncated]" if len(text) > MAX_CONTEXT_CHARS else "")


def render(rt: "Runtime", ctx: "ExecContext") -> tuple[str, str]:
    cmd = ctx.cmd
    tpl = cmd.prompt or ""
    values = {
        "command": cmd.name,
        "artifact_id": ctx.artifact_id or "(new)",
        "target": ctx.target if isinstance(ctx.target, str) else _j(ctx.target),
        "parameters": _j({k: v for k, v in ctx.params.items() if cmd["parameters"][k].get("type") != "path"}),
        "spec": _j(ctx.spec),
        "tests": tests_summary(ctx.test),
        "expected_ids": ", ".join(requirement_ids(ctx.spec)) or "none",
        "workspace_state": workspace_state(ctx),
    }
    for name, ps in cmd["parameters"].items():
        values[name] = _value(rt, ps, ctx.params.get(name))
    if "$context" in tpl or "${context}" in tpl:  # only computed when the template uses it
        values["context"] = artifact_context(rt, ctx)
    system = Template(SYSTEM_PROMPT.read_text(encoding="utf-8")).safe_substitute(values)
    return system, Template(tpl).safe_substitute(values)
