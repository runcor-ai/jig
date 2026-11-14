"""Sequential script execution.

Artifact binding: a script may create an artifact and then refer to it by a
literal id it has not seen yet, e.g.

    requirement("Build a customer management application", ...)
    design("CRM-001")

Before executing anything, the runner pairs each artifact-creating statement
with the first not-yet-existing literal id used *after* it, so `requirement`
allocates exactly CRM-001. If that id already exists the script is refused
(E_ARTIFACT_EXISTS) unless --replace is given, which archives the old artifact
(non-destructively) first. Scripts may also bind variables:  crm = requirement(...).

Variables can also be supplied from outside (one row of a batch file), e.g.
    research(topic, question=question)
and --resume skips every step whose stage already completed with the same parameters.
"""
from __future__ import annotations

from typing import Any, Callable

from .errors import LatticeError
from .parser import ParseError, Ref, Statement, parse
from .runtime import Runtime
from .store import ID_RE

HALT_STATUSES = {"failed", "blocked", "awaiting_approval", "unavailable"}


def _literal_ids(st: Statement) -> list[str]:
    return [st.target] if isinstance(st.target, str) and ID_RE.match(st.target) else []


def _explicit_id(st: Statement, variables: dict) -> str | None:
    v = st.kwargs.get("id")
    if isinstance(v, Ref):
        v = variables.get(v.name)
    return v if isinstance(v, str) and v else None


def plan_bindings(rt: Runtime, stmts: list[Statement], replace: bool, variables: dict | None = None,
                  allow_existing: bool = False) -> dict[int, str]:
    variables = variables or {}
    replace = replace or allow_existing
    creators = [i for i, s in enumerate(stmts)
                if rt.registry.commands[s.command]["artifact"] == "create" and not _explicit_id(s, variables)]
    explicit = {_explicit_id(s, variables) for s in stmts if _explicit_id(s, variables)}
    first_use: dict[str, int] = {}
    for i, s in enumerate(stmts):
        for aid in _literal_ids(s):
            first_use.setdefault(aid, i)
    bindings: dict[int, str] = {}
    used: set[str] = set()
    for n, ci in enumerate(creators):
        nxt = creators[n + 1] if n + 1 < len(creators) else len(stmts)
        # first literal id first-used between this creator and the next one
        cands = [aid for aid, idx in sorted(first_use.items(), key=lambda kv: kv[1])
                 if ci < idx < nxt and aid not in used and aid not in explicit]
        if not cands:
            continue
        aid = cands[0]
        if rt.store.exists(aid) and not replace:
            raise LatticeError("E_ARTIFACT_EXISTS",
                               f"line {stmts[ci].line} would create {aid}, which already exists. Use --replace "
                               f"to archive it and start over, or pass id=\"...\" to create a different artifact")
        bindings[ci] = aid
        used.add(aid)
    for aid in explicit:
        if rt.store.exists(aid) and not replace:
            raise LatticeError("E_ARTIFACT_EXISTS", f"script creates {aid}, which already exists")
    return bindings


def run_script(rt: Runtime, source: str, replace: bool = False, continue_on_error: bool = False,
               on_start: Callable[[Statement], None] | None = None,
               on_result: Callable[[Statement, dict], None] | None = None,
               variables: dict[str, Any] | None = None, resume: bool = False) -> dict:
    variables = dict(variables or {})
    try:
        stmts = parse(source, set(rt.registry.commands), predefined=set(variables))
    except ParseError as e:
        return {"status": "failed", "error": {"code": "E_PARSE", "message": str(e)}, "results": []}
    # Detect ids that already exist but would be re-created (requires --replace or --resume).
    try:
        bindings = plan_bindings(rt, stmts, replace, variables, allow_existing=resume)
    except LatticeError as e:
        return {"status": "failed", "error": e.to_dict(), "results": []}
    if replace:
        for aid in list(bindings.values()) + [a for s in stmts if (a := _explicit_id(s, variables))]:
            if rt.store.exists(aid):
                rt.store.archive_artifact(aid)
    bound: set[str] = set()   # names bound by `x = command(...)` (must hold an artifact id)
    results = []
    status = "completed"
    for i, st in enumerate(stmts):
        try:
            target = _resolve(st.target, variables, bound)
            kwargs = {k: _resolve(v, variables, bound) for k, v in st.kwargs.items()}
        except LatticeError as e:
            results.append({"line": st.line, "source": st.source,
                            "result": {"command": st.command, "status": "failed", "error": e.to_dict()}})
            status = "failed"
            break
        context = {"declared_id": bindings[i]} if i in bindings else {}
        context["script_line"] = st.line
        if on_start:
            on_start(st)
        done = _already_completed(rt, st.command, target, kwargs, context) if resume else None
        res = done or rt.execute(rt.normalize(st.command, target, kwargs, context))
        results.append({"line": st.line, "source": st.source, "result": res})
        if on_result:
            on_result(st, res)
        if st.bind:
            variables[st.bind] = res.get("artifact_id")
            bound.add(st.bind)
        if res["status"] in HALT_STATUSES:
            status = "failed"
            if not continue_on_error:
                break
    return {"status": status, "bindings": {stmts[i].source.split("(")[0] + f"@{stmts[i].line}": a
                                           for i, a in bindings.items()},
            "executed": len(results), "total": len(stmts), "results": results}


def _already_completed(rt: Runtime, command: str, target: Any, kwargs: dict, context: dict) -> dict | None:
    """For --resume: a result stub if this exact step already completed for its artifact."""
    spec = rt.registry.commands[command]
    if spec["execution"]["mode"] == "native":
        return None
    if spec["artifact"] == "create":
        aid = kwargs.get("id") or context.get("declared_id")
    else:
        aid = target if isinstance(target, str) and ID_RE.match(target) else None
    if not aid or not rt.store.exists(aid):
        return None
    st = rt.store.manifest(aid)["stages"].get(command)
    if not st or st["status"] != "completed":
        return None
    try:
        params = rt._validate_params(command, spec, dict(kwargs))
    except LatticeError:
        return None
    if st.get("params") is not None and st["params"] != params:
        return None  # inputs changed: run it again
    return {"command": command, "status": "completed", "skipped": True, "artifact_id": aid,
            "output": None, "validation": {"passed": True, "findings": []},
            "execution": {"model": None, "duration_ms": None, "token_usage": None, "cost_usd": None,
                          "run_id": st["run_id"], "note": "resumed: stage already completed"},
            "error": None}


def _resolve(v: Any, variables: dict, bound: set[str] = frozenset()) -> Any:
    if isinstance(v, Ref):
        if v.name in bound and variables.get(v.name) is None:
            raise LatticeError("E_PARAM", f"variable '{v.name}' has no artifact (its command did not create one)")
        return variables.get(v.name)
    if isinstance(v, list):
        return [_resolve(x, variables, bound) for x in v]
    if isinstance(v, dict):
        return {k: _resolve(x, variables, bound) for k, x in v.items()}
    return v
