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

SKIP_DIRS = {"node_modules", "target", ".git", "dist", "build", ".lattice", ".mvn", "test-results", "coverage"}


@dataclass
class ValidationContext:
    command: str
    output: Any
    params: dict
    workspace: Path | None = None
    spec: dict | None = None        # output of the artifact's `specify` stage
    test: dict | None = None        # output of the artifact's `test` stage
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


def requirement_ids(spec: dict | None) -> list[str]:
    return [r["id"] for r in (spec or {}).get("requirements", [])]


def resolve_in_workspace(ws: Path, p: str) -> Path | None:
    """Resolve an agent-supplied path inside the workspace; None if it escapes."""
    if not p:
        return None
    p = p.strip().replace("\\", "/")
    p = re.sub(r":\d+(-\d+)?$", "", p)   # strip trailing :line
    while p.startswith("./"):
        p = p[2:]
    if p.startswith("/workspace/"):   # path as seen inside the --sandbox docker container
        p = p[len("/workspace/"):]
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
def constraints_reflected(ctx):
    """Every caller constraint must be restated in constraints_applied."""
    got = {_norm(c.get("constraint", "")) for c in ctx.output.get("constraints_applied", [])}
    return [finding("constraints_reflected", f"constraint '{c}' is not addressed in constraints_applied")
            for c in ctx.params.get("constraints", []) if _norm(c) not in got]



@validator
def unique_ids(ctx):
    dup = [i for i, n in Counter(_ids(ctx.output)).items() if n > 1]
    return [finding("unique_ids", f"duplicate ids: {', '.join(sorted(dup))}")] if dup else []


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
        if s["type"] == "junit" and not s.get("tests"):
            out.append(finding("tests_executed", f"'{s['name']}' produced no test results"))
    return out


# ── verify ──────────────────────────────────────────────────────────────
@validator
def verify_covers_all_items(ctx):
    got = {i["id"] for i in ctx.output.get("items", [])}
    want = requirement_ids(ctx.spec)
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
