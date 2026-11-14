"""Prompt rendering. Templates live in lattice/prompts/*.md and use $placeholders."""
from __future__ import annotations

import json
from string import Template
from typing import TYPE_CHECKING

from .config import PROMPT_DIR
from .profiles import enabled_controls, stack_terms
from .validators import verify_expected_ids

if TYPE_CHECKING:
    from .runtime import ExecContext, Runtime

MAX_CONTEXT_CHARS = 120_000


def _tpl(name: str) -> Template:
    return Template((PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8"))


def _j(obj) -> str:
    return json.dumps(obj, indent=1, ensure_ascii=False) if obj is not None else "none"


def decision_model_section(ctx: "ExecContext") -> str:
    dm = ctx.decision_model
    if not dm:
        return ""
    return _tpl("decision_model").safe_substitute(model_name=dm["name"], model_version=dm.get("version", ""),
                                                  model=_j({k: v for k, v in dm.items() if k != "name"}))


def tests_summary(test: dict | None) -> str:
    if not test:
        return "No test results have been recorded for this artifact."
    return _j({"passed": test.get("passed"), "totals": test.get("totals"),
               "suites": [{k: s.get(k) for k in ("name", "status", "tests", "failures", "errors")}
                          for s in test.get("suites", [])],
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
    parts = {}
    for stage in ctx.manifest.get("stages", {}):
        out = rt.store.stage_output(ctx.artifact_id, stage)
        parts[stage] = out
    text = _j(parts)
    if len(text) > MAX_CONTEXT_CHARS:
        text = text[:MAX_CONTEXT_CHARS] + "\n...[truncated]"
    return text


def render(rt: "Runtime", ctx: "ExecContext") -> tuple[str, str]:
    p = ctx.params
    contract = (ctx.stack or {}).get("contract") or {}
    name = ctx.prompt_override or (ctx.command if (PROMPT_DIR / f"{ctx.command}.md").exists() else "generic")
    values = {
        "command": ctx.command,
        "artifact_id": ctx.artifact_id or "(new)",
        "target": ctx.target if isinstance(ctx.target, str) else _j(ctx.target),
        "profile": _j(ctx.profile),
        "stack": _j(ctx.stack),
        "stack_name": (ctx.stack or {}).get("name", "none"),
        "controls": ", ".join(enabled_controls(ctx.profile)) or "none",
        "stack_terms": ", ".join(stack_terms(ctx.stack)) or "none",
        "requirement": _j(ctx.requirement),
        "design": _j(ctx.design),
        "tests": tests_summary(ctx.test),
        "criteria": ", ".join(p.get("criteria", [])),
        "against": p.get("against", ""),
        "expected_ids": ", ".join(verify_expected_ids(ctx.requirement, ctx.design, p.get("against", "requirements"))),
        "notes": p.get("notes") or "none",
        "brief": rt.read_untrusted(p.get("brief")) if p.get("brief") else "none",
        "contract_rules": "\n".join(f"- {r}" for r in contract.get("rules", [])) or "- none",
        "build_steps": "\n".join(f"{i + 1}. {s}" for i, s in enumerate(contract.get("build_steps", []))) or
                       "1. Implement the design and its tests, run the tests and fix failures until they pass.",
        "workspace_state": workspace_state(ctx),
        "decision_model_section": decision_model_section(ctx),
        "purpose": ctx.spec["purpose"],
        "parameters": _j({k: v for k, v in p.items() if k not in ("source", "brief")}),
        "context": artifact_context(rt, ctx) if name in ("generic", "research") else "",
        "source_section": (f"\nSource document:\n<data name=\"source\">{rt.read_untrusted(p['source'])}</data>\n"
                           if p.get("source") else ""),
        "failures": _j((ctx.test or {}).get("failed_cases")),
        "min_sources": p.get("min_sources") or 3,
    }
    system = _tpl("system").safe_substitute(values)
    return system, _tpl(name).safe_substitute(values)
