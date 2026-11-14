"""Semantic validators. Each takes a ValidationContext and returns findings.

These are deterministic checks run *after* JSON-schema validation. Many check
claims against the real filesystem so an agent cannot report success that the
workspace does not support.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml

from .profiles import enabled_controls, stack_terms

SKIP_DIRS = {"node_modules", "target", ".git", "dist", "build", ".lattice", ".mvn", "test-results", "coverage"}


@dataclass
class ValidationContext:
    command: str
    output: Any
    params: dict
    workspace: Path | None = None
    profile: dict | None = None
    stack: dict | None = None
    requirement: dict | None = None
    design: dict | None = None
    test: dict | None = None
    decision_model: dict | None = None
    extra: dict = field(default_factory=dict)


def finding(rule: str, message: str, severity: str = "error") -> dict:
    return {"rule": rule, "severity": severity, "message": message}


VALIDATORS: dict[str, Callable[[ValidationContext], list[dict]]] = {}


def validator(fn):
    VALIDATORS[fn.__name__] = fn
    return fn


def _ids(obj: Any) -> list[str]:
    out = []
    if isinstance(obj, dict):
        if isinstance(obj.get("id"), str):
            out.append(obj["id"])
        for v in obj.values():
            out += _ids(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _ids(v)
    return out


def fr_ids(req: dict | None) -> list[str]:
    return [r["id"] for r in (req or {}).get("functional_requirements", [])]


def resolve_in_workspace(ws: Path, p: str) -> Path | None:
    """Resolve an agent-supplied path inside the workspace; None if it escapes."""
    if not p:
        return None
    p = p.strip().replace("\\", "/")
    p = re.sub(r":\d+(-\d+)?$", "", p)   # strip trailing :line
    while p.startswith("./"):
        p = p[2:]
    cand = Path(p)
    if not cand.is_absolute():
        cand = ws / p
    try:
        cand = cand.resolve()
        cand.relative_to(ws.resolve())
    except (ValueError, OSError):
        return None
    return cand


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


# ── generic ─────────────────────────────────────────────────────────────
@validator
def unique_ids(ctx):
    dup = [i for i, n in Counter(_ids(ctx.output)).items() if n > 1]
    return [finding("unique_ids", f"duplicate ids: {', '.join(sorted(dup))}")] if dup else []


# ── requirement ─────────────────────────────────────────────────────────
@validator
def acceptance_criteria_reference_requirements(ctx):
    out = []
    frs = set(fr_ids(ctx.output))
    covered = set()
    for ac in ctx.output.get("acceptance_criteria", []):
        bad = [v for v in ac.get("verifies", []) if v.startswith("FR-") and v not in frs]
        if bad:
            out.append(finding("acceptance_criteria_reference_requirements",
                               f"{ac['id']} references unknown requirements {bad}"))
        covered |= set(ac.get("verifies", []))
    for fr in ctx.output.get("functional_requirements", []):
        if fr["priority"] == "must" and fr["id"] not in covered:
            out.append(finding("acceptance_criteria_reference_requirements",
                               f"must-have {fr['id']} is not verified by any acceptance criterion", "warning"))
    return out


@validator
def profile_controls_reflected(ctx):
    out = []
    sources = " ".join((n.get("source") or "") for n in ctx.output.get("non_functional_requirements", []))
    for c in enabled_controls(ctx.profile):
        if c not in sources:
            out.append(finding("profile_controls_reflected",
                               f"profile control '{c}' is not reflected by any NFR (expected source 'profile:{c}')"))
    return out


@validator
def stack_reflected(ctx):
    text = _norm(" ".join(c.get("description", "") for c in ctx.output.get("constraints", [])))
    return [finding("stack_reflected", f"stack component '{t}' missing from constraints")
            for t in stack_terms(ctx.stack) if _norm(t) not in text]


# ── design ──────────────────────────────────────────────────────────────
@validator
def design_traces_all_requirements(ctx):
    traced = {t["requirement"] for t in ctx.output.get("traceability", [])}
    out = [finding("design_traces_all_requirements", f"{fr} has no traceability entry")
           for fr in fr_ids(ctx.requirement) if fr not in traced]
    comp_keys = {c["id"] for c in ctx.output.get("components", [])} | {c["name"] for c in ctx.output.get("components", [])}
    for t in ctx.output.get("traceability", []):
        unknown = [c for c in t.get("components", []) if c not in comp_keys]
        if unknown:
            out.append(finding("design_traces_all_requirements",
                               f"traceability for {t['requirement']} names unknown components {unknown}", "warning"))
    return out


@validator
def design_resolves_open_decisions(ctx):
    decided = {d["id"] for d in ctx.output.get("decisions", [])}
    return [finding("design_resolves_open_decisions", f"open decision {d['id']} ({d['question']}) not resolved")
            for d in (ctx.requirement or {}).get("open_decisions", []) if d["id"] not in decided]


@validator
def design_layout_matches_stack_contract(ctx):
    contract = (ctx.stack or {}).get("contract") or {}
    layout = [l["path"].replace("\\", "/").removeprefix("./").rstrip("/")
              for l in ctx.output.get("repository_layout", [])]
    out = []
    for req in contract.get("required_paths", []):
        top = req.split("/")[0]
        if not any(p == req or p.startswith(top) for p in layout):
            out.append(finding("design_layout_matches_stack_contract", f"repository_layout lacks '{req}'"))
    return out


@validator
def design_endpoints_reference_requirements(ctx):
    frs = set(fr_ids(ctx.requirement))
    out = []
    for ep in ctx.output.get("api", []):
        bad = [r for r in ep.get("requirements", []) if r.startswith("FR-") and r not in frs]
        if bad:
            out.append(finding("design_endpoints_reference_requirements",
                               f"{ep['method']} {ep['path']} references unknown {bad}", "warning"))
    return out


# ── build ───────────────────────────────────────────────────────────────
@validator
def stack_contract_files_exist(ctx):
    contract = (ctx.stack or {}).get("contract") or {}
    paths = contract.get("required_paths", [])
    return [finding("stack_contract_files_exist", f"required file '{p}' does not exist in workspace")
            for p in paths if not (ctx.workspace / p).exists()]


@validator
def compose_services_present(ctx):
    contract = (ctx.stack or {}).get("contract") or {}
    if not contract.get("compose_services"):
        return []
    f = ctx.workspace / contract.get("compose_file", "docker-compose.yml")
    if not f.exists():
        return [finding("compose_services_present", f"{f.name} missing")]
    try:
        services = (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("services", {}) or {}
    except yaml.YAMLError as e:
        return [finding("compose_services_present", f"{f.name} is not valid YAML: {e}")]
    return [finding("compose_services_present", f"compose service '{s}' missing")
            for s in contract.get("compose_services", []) if s not in services]


@validator
def migrations_present(ctx):
    g = ((ctx.stack or {}).get("contract") or {}).get("migrations_glob")
    if not g:
        return []
    return [] if list(ctx.workspace.glob(g)) else [finding("migrations_present", f"no migrations match {g}")]


@validator
def claimed_files_exist(ctx):
    claimed = list(ctx.output.get("files_created", []))
    for r in ctx.output.get("requirements_implemented", []):
        claimed += r.get("evidence_paths", [])
    claimed = sorted(set(claimed))
    missing = [p for p in claimed if not ((rp := resolve_in_workspace(ctx.workspace, p)) and rp.exists())]
    if not missing:
        return []
    sev = "error" if len(missing) > max(2, 0.1 * len(claimed)) else "warning"
    return [finding("claimed_files_exist", f"{len(missing)}/{len(claimed)} claimed paths do not exist: "
                                           f"{missing[:15]}", sev)]


SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"), "private key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key id"),
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"), "Anthropic API key"),
    (re.compile(r"ghp_[A-Za-z0-9]{36}"), "GitHub token"),
]


def iter_files(ws: Path):
    for p in ws.rglob("*"):
        if any(part in SKIP_DIRS for part in p.relative_to(ws).parts):
            continue
        if p.is_file() and p.stat().st_size < 2_000_000:
            yield p


@validator
def no_secrets_in_workspace(ctx):
    out = []
    for p in iter_files(ctx.workspace):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for rx, label in SECRET_PATTERNS:
            if rx.search(text):
                out.append(finding("no_secrets_in_workspace", f"possible {label} in {p.relative_to(ctx.workspace)}"))
    return out


# ── review ──────────────────────────────────────────────────────────────
@validator
def all_criteria_assessed(ctx):
    got = {_norm(c["criterion"]) for c in ctx.output.get("criteria_assessed", [])}
    return [finding("all_criteria_assessed", f"criterion '{c}' not assessed")
            for c in ctx.params.get("criteria", []) if _norm(c) not in got]


def _check_file_line(ws: Path, file: str, line: int | None, rule: str, who: str) -> list[dict]:
    rp = resolve_in_workspace(ws, file)
    if rp is None or not rp.is_file():
        return [finding(rule, f"{who} cites '{file}', which does not exist in the workspace")]
    if line:
        n = sum(1 for _ in rp.open(encoding="utf-8", errors="ignore"))
        if line > n:
            return [finding(rule, f"{who} cites {file}:{line} but the file has {n} lines")]
    return []


@validator
def findings_cite_existing_files(ctx):
    out = []
    for f in ctx.output.get("findings", []):
        if not f.get("file"):
            out.append(finding("findings_cite_existing_files", f"{f['id']} cites no file", "warning"))
            continue
        out += _check_file_line(ctx.workspace, f["file"], f.get("line"), "findings_cite_existing_files", f["id"])
    return out


# ── test ────────────────────────────────────────────────────────────────
@validator
def tests_executed(ctx):
    out = []
    for s in ctx.output.get("suites", []):
        if s["type"] == "junit" and s["status"] != "skipped" and not s.get("tests"):
            out.append(finding("tests_executed", f"suite '{s['name']}' produced no test results"))
    return out


# ── verify ──────────────────────────────────────────────────────────────
def verify_expected_ids(req: dict | None, design: dict | None, against: str) -> list[str]:
    if against == "design":
        return [f"{e['method']} {e['path']}" for e in (design or {}).get("api", [])]
    return fr_ids(req) + [a["id"] for a in (req or {}).get("acceptance_criteria", [])]


@validator
def verify_covers_all_items(ctx):
    got = {i["id"] for i in ctx.output.get("items", [])}
    want = verify_expected_ids(ctx.requirement, ctx.design, ctx.params.get("against", "requirements"))
    return [finding("verify_covers_all_items", f"'{w}' was not verified") for w in want if w not in got]


@validator
def evidence_files_exist(ctx):
    out = []
    for it in ctx.output.get("items", []):
        for ev in it.get("evidence", []):
            out += _check_file_line(ctx.workspace, ev["file"], None, "evidence_files_exist", it["id"])
    return out


@validator
def evidence_symbols_exist(ctx):
    out = []
    for it in ctx.output.get("items", []):
        for ev in it.get("evidence", []):
            sym = (ev.get("symbol") or "").strip()
            rp = resolve_in_workspace(ctx.workspace, ev["file"])
            if not sym or rp is None or not rp.is_file():
                continue
            text = rp.read_text(encoding="utf-8", errors="ignore")
            # Accept "Class.method", "Class#method" or "method()" style references.
            parts = [p for p in re.split(r"[.#():\s]+", sym) if p]
            if parts and not all(p in text for p in parts):
                out.append(finding("evidence_symbols_exist", f"{it['id']}: symbol '{sym}' not found in {ev['file']}"))
    return out


@validator
def test_evidence_matches_results(ctx):
    cited = [(it["id"], t) for it in ctx.output.get("items", []) for t in it.get("test_evidence", [])]
    if not cited:
        return []
    names = (ctx.test or {}).get("case_names", [])
    if not names:
        return [finding("test_evidence_matches_results",
                        f"{len(cited)} test citations but no recorded test results to check them against")]
    normed = [_norm(n) for n in names]
    out = []
    for iid, t in cited:
        key = _norm(t.split("(")[0])
        if not any(key and (key in n or n.endswith(key)) for n in normed):
            out.append(finding("test_evidence_matches_results", f"{iid}: cited test '{t}' not in recorded results"))
    return out


# ── decision ────────────────────────────────────────────────────────────
@validator
def decision_model_complete(ctx):
    dm = ctx.decision_model
    if not dm:
        return [finding("decision_model_complete", "no decision model resolved")]
    out = []
    options = [o["name"] for o in ctx.output.get("options", [])]
    scored = {(_norm(s["option"]), _norm(s["criterion"])) for s in ctx.output.get("criteria_scores", [])}
    for o in options:
        for c in dm["criteria"]:
            if (_norm(o), _norm(c)) not in scored:
                out.append(finding("decision_model_complete", f"option '{o}' not scored on '{c}'"))
    rec = ctx.output.get("recommendation", {}).get("option", "")
    if options and _norm(rec) not in {_norm(o) for o in options}:
        out.append(finding("decision_model_complete", f"recommended option '{rec}' is not one of the options"))
    if dm.get("assumptions_required") and not ctx.output.get("assumptions"):
        out.append(finding("decision_model_complete", "model requires stated assumptions; none given"))
    return out


# ── research ────────────────────────────────────────────────────────────
@validator
def research_findings_sourced(ctx):
    ids = {s["id"] for s in ctx.output.get("sources", [])}
    out = []
    for f in ctx.output.get("findings", []):
        if not f.get("source_ids"):
            out.append(finding("research_findings_sourced", f"{f['id']} cites no source"))
        bad = [s for s in f.get("source_ids", []) if s not in ids]
        if bad:
            out.append(finding("research_findings_sourced", f"{f['id']} cites unknown sources {bad}"))
    return out


@validator
def research_min_sources(ctx):
    want = int(ctx.params.get("min_sources") or 0)
    urls = {_url_key(s["url"]) for s in ctx.output.get("sources", [])}
    return [finding("research_min_sources", f"{len(urls)} distinct sources, {want} required")] if len(urls) < want else []


def _url_key(u: str) -> str:
    u = u.strip().split("#")[0]
    return re.sub(r"^https?://(www\.)?", "", u, flags=re.I).rstrip("/").lower()


@validator
def research_sources_retrieved(ctx):
    """Every cited URL must appear in this session's own tool calls/results (anti-fabrication)."""
    path = (ctx.extra or {}).get("agent_events")
    if not path or not Path(path).exists():
        return [finding("research_sources_retrieved", "no agent event log available; sources cannot be verified")]
    raw = Path(path).read_text(encoding="utf-8", errors="ignore")
    decoded = []
    for line in raw.splitlines():  # decode \uXXXX escapes so URLs match as written
        try:
            decoded.append(json.dumps(json.loads(line), ensure_ascii=False))
        except json.JSONDecodeError:
            pass
    # Collapse any JSON-escaped slashes (https:\/\/ or https:\\/\\/) to plain ones.
    hay = re.sub(r"\\+/", "/", raw + "\n" + "\n".join(decoded)).lower()
    out = []
    for s in ctx.output.get("sources", []):
        key = _url_key(s["url"])
        if not key or key not in hay:
            out.append(finding("research_sources_retrieved",
                               f"{s['id']} {s['url']} does not appear in this session's searches or fetches"))
    return out
