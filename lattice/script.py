"""Sequential script execution.

Binding results to variables (preferred):

    spec = specify("A simple Pong game", constraints=["React + TypeScript"], id="PONG-001")
    build(spec)                         # a bound result passed as a value means its artifact id
    test(spec)
    research(spec.output.title)         # dotted lookups read the bound result's data

A bound variable exposes:  .id (artifact id), .status, .command, .output.<field>...
Variables can also be supplied from outside (one row of a batch file):  research(topic, question=question)

Literal ids also work. A creating command followed by a literal id that does not exist yet
(`specify(...)` then `build("PONG-001")`) allocates exactly that id. Re-creating an existing id is
refused (E_ARTIFACT_EXISTS) unless --replace (archives the old artifact) or --resume (skips steps that
already completed with the same inputs) is given.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .errors import LatticeError
from .parser import ParseError, Ref, Statement, parse
from .runtime import Runtime
from .store import ID_RE

HALT_STATUSES = {"failed", "blocked", "unavailable"}


@dataclass
class Bound:
    """The result of `x = command(...)`, as seen by later statements."""
    result: dict

    def view(self) -> dict:
        r = self.result
        return {"id": r.get("artifact_id"), "artifact_id": r.get("artifact_id"), "status": r.get("status"),
                "command": r.get("command"), "output": r.get("output")}


def _literal_ids(st: Statement) -> list[str]:
    return [st.target] if isinstance(st.target, str) and ID_RE.match(st.target) else []


def _explicit_id(st: Statement, variables: dict) -> str | None:
    v = st.kwargs.get("id")
    if isinstance(v, Ref):
        try:
            v = _lookup(v, variables)
        except LatticeError:
            return None
    return v if isinstance(v, str) and v else None


def plan_bindings(rt: Runtime, stmts: list[Statement], replace: bool, variables: dict | None = None,
                  allow_existing: bool = False) -> dict[int, str]:
    variables = variables or {}
    replace = replace or allow_existing
    creators = [i for i, s in enumerate(stmts)
                if rt.commands[s.command]["artifact"] == "create" and not _explicit_id(s, variables)]
    explicit = {_explicit_id(s, variables) for s in stmts if _explicit_id(s, variables)}
    first_use: dict[str, int] = {}
    for i, s in enumerate(stmts):
        for aid in _literal_ids(s):
            first_use.setdefault(aid, i)
    bindings: dict[int, str] = {}
    used: set[str] = set()
    for n, ci in enumerate(creators):
        nxt = creators[n + 1] if n + 1 < len(creators) else len(stmts)
        cands = [aid for aid, idx in sorted(first_use.items(), key=lambda kv: kv[1])
                 if ci < idx < nxt and aid not in used and aid not in explicit]
        if not cands:
            continue
        aid = cands[0]
        if rt.store.exists(aid) and not replace:
            raise LatticeError("E_ARTIFACT_EXISTS",
                               f"line {stmts[ci].line} would create {aid}, which already exists. Use --replace "
                               f"to archive it and start over, --resume to continue it, or a different id")
        bindings[ci] = aid
        used.add(aid)
    for aid in explicit:
        if rt.store.exists(aid) and not replace:
            raise LatticeError("E_ARTIFACT_EXISTS", f"script creates {aid}, which already exists. Use --replace "
                                                    f"to start over or --resume to continue it")
    return bindings


def run_script(rt: Runtime, source: str, replace: bool = False, continue_on_error: bool = False,
               on_start: Callable[[Statement], None] | None = None,
               on_result: Callable[[Statement, dict], None] | None = None,
               variables: dict[str, Any] | None = None, resume: bool = False) -> dict:
    variables = dict(variables or {})
    try:
        stmts = parse(source, set(rt.commands), predefined=set(variables))
    except ParseError as e:
        return {"status": "failed", "error": {"code": "E_PARSE", "message": str(e)}, "results": []}
    try:
        bindings = plan_bindings(rt, stmts, replace, variables, allow_existing=resume)
    except LatticeError as e:
        return {"status": "failed", "error": e.to_dict(), "results": []}
    if replace:
        for aid in list(bindings.values()) + [a for s in stmts if (a := _explicit_id(s, variables))]:
            if rt.store.exists(aid):
                rt.store.archive_artifact(aid)
    results = []
    status = "completed"
    for i, st in enumerate(stmts):
        try:
            target = _resolve(st.target, variables)
            kwargs = {k: _resolve(v, variables) for k, v in st.kwargs.items()}
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
            variables[st.bind] = Bound(res)
        if res["status"] in HALT_STATUSES:
            status = "failed"
            if not continue_on_error:
                break
    return {"status": status, "bindings": {stmts[i].source.split("(")[0] + f"@{stmts[i].line}": a
                                           for i, a in bindings.items()},
            "executed": len(results), "total": len(stmts), "results": results}


def _already_completed(rt: Runtime, command: str, target: Any, kwargs: dict, context: dict) -> dict | None:
    """For --resume: the stored result if this exact step already completed for its artifact."""
    cmd = rt.commands[command]
    if cmd["artifact"] == "create":
        aid = kwargs.get("id") or context.get("declared_id")
    else:
        aid = target if isinstance(target, str) and ID_RE.match(target) else None
    if not aid or not rt.store.exists(aid):
        return None
    st = rt.store.manifest(aid)["stages"].get(command)
    if not st or st["status"] != "completed":
        return None
    try:
        params = rt._validate_params(cmd, dict(kwargs))
    except LatticeError:
        return None
    if st.get("params") is not None and st["params"] != params:
        return None  # inputs changed: run it again
    return {"command": command, "status": "completed", "skipped": True, "artifact_id": aid,
            "output": rt.store.stage_output(aid, command), "validation": {"passed": True, "findings": []},
            "execution": {"model": None, "duration_ms": None, "token_usage": None, "cost_usd": None,
                          "run_id": st["run_id"], "note": "resumed: stage already completed"},
            "error": None}


def _lookup(ref: Ref, variables: dict) -> Any:
    if ref.name not in variables:
        raise LatticeError("E_PARAM", f"variable '{ref.name}' is not defined")
    val = variables[ref.name]
    if isinstance(val, Bound):
        if not ref.path:  # the variable itself stands for its artifact
            if not val.result.get("artifact_id"):
                raise LatticeError("E_PARAM", f"'{ref.name}' has no artifact (its command did not create one); "
                                              f"use {ref.name}.output.<field> to pass data instead")
            return val.result["artifact_id"]
        if ref.path[0] == "output" and val.result.get("output") is None:
            raise LatticeError("E_PARAM", f"'{ref}' not found: '{ref.name}' has no output (its "
                                          f"{val.result.get('command')} step ended '{val.result.get('status')}')")
        val = val.view()
    for i, key in enumerate(ref.path):
        if isinstance(val, dict) and key in val:
            val = val[key]
        else:
            where = ".".join((ref.name, *ref.path[:i]))
            keys = sorted(val) if isinstance(val, dict) else type(val).__name__
            raise LatticeError("E_PARAM", f"'{ref}' not found: '{where}' has no '{key}' (available: {keys})")
    return val


def _resolve(v: Any, variables: dict) -> Any:
    if isinstance(v, Ref):
        return _lookup(v, variables)
    if isinstance(v, list):
        return [_resolve(x, variables) for x in v]
    if isinstance(v, dict):
        return {k: _resolve(x, variables) for k, x in v.items()}
    return v
