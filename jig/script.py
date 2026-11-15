"""Script execution: an interpreter for the Jig language (see docs/language.md).

Binding results to variables:

    spec = specify("A simple Pong game", constraints=["React + TypeScript"], id="PONG-001")
    build(spec)                         # a bound result passed to a command means its artifact id
    v = verify(spec)
    tries = 0
    while v.output.verdict != "pass" and tries < 3:
        build(spec, notes=v.output.summary)
        v = verify(spec)
        tries += 1

A bound result exposes:  .id (artifact id), .status, .command, .output.<field>...
Variables can also be supplied from outside (one row of a batch file):  research(topic, question=question)

Only command calls cost anything; everything else (if/for/while, arithmetic, lists, maps,
queues, sets) runs locally. Limits from config `script:` stop runaway scripts.

Literal ids also work. A top-level creating command followed by a literal id that does not exist
yet (`specify(...)` then `build("PONG-001")`) allocates exactly that id. Re-creating an existing id
is refused (E_ARTIFACT_EXISTS) unless --replace (archives the old artifact) or --resume is given.

--resume replays the previous run of the same script with the same variables: steps are matched
in execution order (command + inputs) and completed ones are reused, up to the first step that
differs; from there everything runs for real. Each run's step journal is kept in
<store>/scripts/<key>.json.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable

from .datatypes import BUILTINS, Limits, Queue, call_method, fail, guard, precheck, type_name
from .datatypes import truthy as data_truthy
from .errors import JigError
from .parser import (Assign, Attr, AugAssign, BinOp, BoolOp, Break, Call, Compare, Cond, Continue, ExprStmt, For,
                     FStr, If, Index, Method, ParseError, Pass, Ref, Slice, Statement, Unary, While, parse, walk)
from .runtime import Runtime
from .store import ID_RE, read_json, write_json

HALT_STATUSES = {"failed", "blocked", "unavailable"}
PY_ERRORS = (TypeError, ValueError, KeyError, IndexError, ZeroDivisionError, OverflowError,
             RecursionError)
SCRIPT_DEFAULTS = {"max_while_iterations": 10, "max_steps": 100_000, "max_items": 100_000, "max_depth": 3}


@dataclass
class Bound:
    """The result of `x = command(...)`, as seen by later statements."""
    result: dict
    name: str = "result"

    def view(self) -> dict:
        r = self.result
        return {"id": r.get("artifact_id"), "artifact_id": r.get("artifact_id"), "status": r.get("status"),
                "command": r.get("command"), "output": copy.deepcopy(r.get("output"))}


class _Break(Exception):
    pass


class _Continue(Exception):
    pass


class _Halt(Exception):
    pass


# ── values ──────────────────────────────────────────────────────────────
def to_data(v: Any) -> Any:
    """Convert a script value to plain JSON data, as passed to a command."""
    if isinstance(v, Bound):
        if not v.result.get("artifact_id"):
            raise JigError("E_PARAM", f"'{v.name}' has no artifact (its command did not create one); "
                                          f"use {v.name}.output.<field> to pass data instead")
        return v.result["artifact_id"]
    if isinstance(v, (list, tuple)):
        return [to_data(x) for x in v]
    if isinstance(v, Queue):
        return [to_data(x) for x in v.items]
    if isinstance(v, set):
        try:
            return sorted(v)
        except TypeError:
            return list(v)
    if isinstance(v, dict):
        return {k: to_data(x) for k, x in v.items()}
    return v


def truthy(v: Any) -> bool:
    if isinstance(v, Bound):
        return v.result.get("status") == "completed"
    return data_truthy(v)


def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _lookup(ref: Ref, variables: dict) -> Any:
    if ref.name not in variables:
        raise JigError("E_PARAM", f"variable '{ref.name}' is not defined")
    val = variables[ref.name]
    if isinstance(val, Bound):
        if not ref.path:
            return val
        if ref.path[0] == "output" and val.result.get("output") is None:
            raise JigError("E_PARAM", f"'{ref}' not found: '{ref.name}' has no output (its "
                                          f"{val.result.get('command')} step ended '{val.result.get('status')}')")
        val = val.view()
    for i, key in enumerate(ref.path):
        if isinstance(val, Bound):
            val = val.view()
        if isinstance(val, dict) and key in val:
            val = val[key]
        else:
            where = ".".join((ref.name, *ref.path[:i]))
            keys = sorted(val) if isinstance(val, dict) else type_name(val)
            raise JigError("E_PARAM", f"'{ref}' not found: '{where}' has no '{key}' (available: {keys})")
    return val


# ── static planning (top level only) ────────────────────────────────────
def _literal_ids(st: Statement) -> list[str]:
    return [st.target] if isinstance(st.target, str) and ID_RE.match(st.target) else []


def _explicit_id(st: Statement, variables: dict) -> str | None:
    v = st.kwargs.get("id")
    if isinstance(v, Ref):
        try:
            v = _lookup(v, variables)
        except JigError:
            return None
    return v if isinstance(v, str) and v else None


def plan_bindings(rt: Runtime, stmts: list[Statement], replace: bool, variables: dict | None = None,
                  allow_existing: bool = False) -> dict[int, str]:
    """Forward-declared literal ids for the straight-line top level of a script."""
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
            raise JigError("E_ARTIFACT_EXISTS",
                               f"line {stmts[ci].line} would create {aid}, which already exists. Use --replace "
                               f"to archive it and start over, --resume to continue it, or a different id")
        bindings[ci] = aid
        used.add(aid)
    for aid in explicit:
        if rt.store.exists(aid) and not replace:
            raise JigError("E_ARTIFACT_EXISTS", f"script creates {aid}, which already exists. Use --replace "
                                                    f"to start over or --resume to continue it")
    return bindings


def _journal_key(script_id: str, variables: dict) -> str:
    raw = json.dumps({"script": script_id, "variables": variables}, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _inputs_hash(command: str, target: Any, kwargs: dict, context: dict) -> str:
    raw = json.dumps({"c": command, "t": target, "k": kwargs, "d": context.get("declared_id")},
                     sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


# ── interpreter ─────────────────────────────────────────────────────────
class Interp:
    def __init__(self, rt: Runtime, variables: dict, *, replace: bool, resume: bool, continue_on_error: bool,
                 on_start, on_result, on_log, bindings: dict[int, str], script_id: str):
        cfg = {**SCRIPT_DEFAULTS, **(rt.config.get("script") or {})}
        self.rt = rt
        self.vars = variables
        self.replace, self.resume, self.continue_on_error = replace, resume, continue_on_error
        self.on_start, self.on_result, self.on_log = on_start, on_result, on_log
        self.bindings = bindings                     # id(Statement) -> declared artifact id
        self.lim = Limits(max_items=int(cfg["max_items"]))
        self.max_while = int(cfg["max_while_iterations"])
        self.max_steps = int(cfg["max_steps"])
        self.steps = 0
        self.results: list[dict] = []
        self.log: list[str] = []
        self.status = "completed"
        self.step_failures = 0
        self.error: dict | None = None
        self.created: set[str] = set()
        # step journal for --resume
        self.journal_path = rt.store.root / "scripts" / f"{_journal_key(script_id, variables)}.json"
        prev = read_json(self.journal_path) if resume else None
        self.prev_steps: list[dict] | None = prev.get("steps") if isinstance(prev, dict) else None
        self.replaying = self.prev_steps is not None
        self.journal = {"script": script_id, "variables": variables, "steps": []}

    # ── statements ──────────────────────────────────────────────────────
    def run(self, stmts: list) -> None:
        try:
            self.block(stmts)
        except _Halt:
            pass

    def block(self, stmts: list) -> None:
        for s in stmts:
            self.exec(s)

    def _script_error(self, s: Any, e: JigError, command: str | None = None) -> None:
        err = e.to_dict()
        err["message"] = f"line {s.line}: {err['message']}" if command is None else err["message"]
        self.results.append({"line": s.line, "source": s.source,
                             "result": {"command": command, "status": "failed", "error": err}})
        self.status = "failed"
        self.error = err
        raise _Halt

    def tick(self, s: Any) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            self._script_error(s, fail(f"the script ran more than {self.max_steps} statements "
                                       f"(config script.max_steps)"))

    def exec(self, s: Any) -> None:
        self.tick(s)
        if isinstance(s, Statement):
            return self.command(s)
        try:
            if isinstance(s, Assign):
                self.assign(s.target, self.eval(s.value))
            elif isinstance(s, AugAssign):
                cur = self.eval(Ref(s.target) if isinstance(s.target, str) else s.target)
                self.assign(s.target, self.binop(s.op, cur, self.eval(s.value)))
            elif isinstance(s, ExprStmt):
                self.eval(s.expr)
            elif isinstance(s, If):
                self.block(s.body if truthy(self.eval(s.test)) else s.orelse)
            elif isinstance(s, For):
                for item in self.iterate(self.eval(s.iter)):
                    self.tick(s)
                    self.assign(s.target, item)
                    try:
                        self.block(s.body)
                    except _Break:
                        break
                    except _Continue:
                        continue
            elif isinstance(s, While):
                n = 0
                while truthy(self.eval(s.test)):
                    n += 1
                    if n > self.max_while:
                        raise fail(f"while loop ran {self.max_while} times and its condition is still true "
                                   f"(config script.max_while_iterations); add a counter to the condition or "
                                   f"use 'for i in range(n)'")
                    try:
                        self.block(s.body)
                    except _Break:
                        break
                    except _Continue:
                        continue
            elif isinstance(s, Break):
                raise _Break
            elif isinstance(s, Continue):
                raise _Continue
            elif isinstance(s, Pass):
                pass
        except JigError as e:
            self._script_error(s, e)
        except PY_ERRORS as e:
            self._script_error(s, fail(f"{type(e).__name__}: {e}"))

    def assign(self, target: Any, value: Any) -> None:
        if isinstance(target, str):
            self.vars[target] = value
        elif isinstance(target, tuple):
            items = value if isinstance(value, list) else None
            if items is None or len(items) != len(target):
                raise fail(f"cannot unpack {type_name(value)} into {len(target)} names")
            for n, x in zip(target, items):
                self.vars[n] = x
        elif isinstance(target, Index):
            base = self.eval(target.base)
            key = self.eval(target.key)
            if isinstance(base, dict):
                if not (isinstance(key, (str, int, float, bool)) or key is None):
                    raise fail(f"map key must be a string, number, bool or null, got {type_name(key)}")
                if key not in base:
                    precheck(len(base) + 1, self.lim, "map")
                base[key] = value
            elif isinstance(base, list):
                if not isinstance(key, int) or isinstance(key, bool) or not -len(base) <= key < len(base):
                    raise fail(f"list index {key!r} is out of range for a list of {len(base)}")
                base[key] = value
            else:
                raise fail(f"cannot assign to an item of a {type_name(base)}")

    def iterate(self, v: Any) -> list:
        if isinstance(v, (list, str)):
            return list(v)
        if isinstance(v, dict):
            return list(v.keys())
        if isinstance(v, Queue):
            return list(v.items)
        if isinstance(v, set):
            return sorted(v, key=lambda x: (type_name(x), str(x)))
        raise fail(f"cannot loop over a {type_name(v)}")

    # ── command steps ───────────────────────────────────────────────────
    def command(self, st: Statement) -> None:
        try:
            target = to_data(self.eval(st.target))
            kwargs = {k: to_data(self.eval(v)) for k, v in st.kwargs.items()}
        except JigError as e:
            self._script_error(st, e, command=st.command)
        except PY_ERRORS as e:
            self._script_error(st, fail(f"line {st.line}: {type(e).__name__}: {e}"), command=st.command)
        context = {"declared_id": self.bindings[id(st)]} if id(st) in self.bindings else {}
        context["script_line"] = st.line
        cmd = self.rt.commands[st.command]
        if self.on_start:
            self.on_start(st)
        k = len(self.journal["steps"])
        h = _inputs_hash(st.command, target, kwargs, context)
        res = self._replay(k, st.command, h)
        if res is None and self.resume and self.prev_steps is None:
            res = _already_completed(self.rt, st.command, target, kwargs, context)   # runs from before journals
        if res is None:
            declared = kwargs.get("id") or context.get("declared_id")
            if cmd["artifact"] == "create" and self.replace and isinstance(declared, str) \
                    and declared not in self.created and self.rt.store.exists(declared):
                self.rt.store.archive_artifact(declared)
            res = self.rt.execute(self.rt.normalize(st.command, target, kwargs, context))
        if cmd["artifact"] == "create" and res.get("artifact_id"):
            self.created.add(res["artifact_id"])
        self.journal["steps"].append({"command": st.command, "line": st.line, "inputs": h,
                                      "status": res.get("status"), "result": res})
        write_json(self.journal_path, self.journal)
        self.results.append({"line": st.line, "source": st.source, "step": k, "result": res})
        if self.on_result:
            self.on_result(st, res)
        if st.bind:
            self.vars[st.bind] = Bound(res, st.bind)
        elif st.bind_target is not None:
            try:
                self.assign(st.bind_target, Bound(res, "result"))
            except JigError as e:
                self._script_error(st, e)
        if res["status"] in HALT_STATUSES:
            self.step_failures += 1
            if not self.continue_on_error:
                self.status = "failed"
                raise _Halt
            # With --continue-on-error the script handles failures itself and decides the outcome
            # (it calls fail("...") when the run as a whole should count as failed).

    def _replay(self, k: int, command: str, h: str) -> dict | None:
        if not self.replaying:
            return None
        prev = self.prev_steps[k] if k < len(self.prev_steps) else None
        ok = (prev and prev.get("command") == command and prev.get("inputs") == h
              and prev.get("status") == "completed")
        aid = (prev or {}).get("result", {}).get("artifact_id")
        if ok and aid and not self.rt.store.exists(aid):
            ok = False
        if not ok:
            self.replaying = False      # from the first difference on, everything runs for real
            return None
        res = copy.deepcopy(prev["result"])
        res["skipped"] = True
        res.setdefault("execution", {})
        res["execution"] = {**(res["execution"] or {}), "note": "resumed: step already completed"}
        return res

    # ── expressions ─────────────────────────────────────────────────────
    def eval(self, e: Any) -> Any:
        if e is None or isinstance(e, (str, int, float, bool)):
            return e
        if isinstance(e, Ref):
            return _lookup(e, self.vars)
        if isinstance(e, list):
            return guard([self.eval(x) for x in e], self.lim)
        if isinstance(e, dict):
            return {k: self.eval(v) for k, v in e.items()}
        if isinstance(e, Attr):
            base = self.eval(e.base)
            if isinstance(base, Bound):
                base = base.view()
            if isinstance(base, dict) and e.name in base:
                return base[e.name]
            keys = sorted(base) if isinstance(base, dict) else type_name(base)
            raise JigError("E_PARAM", f"{type_name(base)} has no '{e.name}' (available: {keys})")
        if isinstance(e, Index):
            return self.index(self.eval(e.base), self.eval(e.key))
        if isinstance(e, Slice):
            base = self.eval(e.base)
            lo, hi = self.eval(e.lo), self.eval(e.hi)
            if not isinstance(base, (list, str)):
                raise fail(f"cannot slice a {type_name(base)}")
            if not all(x is None or (isinstance(x, int) and not isinstance(x, bool)) for x in (lo, hi)):
                raise fail("slice bounds must be integers")
            return base[lo:hi]
        if isinstance(e, BinOp):
            return self.binop(e.op, self.eval(e.left), self.eval(e.right))
        if isinstance(e, Unary):
            v = self.eval(e.operand)
            if e.op == "not":
                return not truthy(v)
            if not _num(v):
                raise fail(f"cannot negate a {type_name(v)}")
            return -v
        if isinstance(e, BoolOp):
            v = None
            for x in e.values:
                v = self.eval(x)
                if (e.op == "and") != truthy(v):
                    return v
            return v
        if isinstance(e, Compare):
            left = self.eval(e.left)
            for op, r in zip(e.ops, e.rights):
                right = self.eval(r)
                if not self.compare(op, left, right):
                    return False
                left = right
            return True
        if isinstance(e, Cond):
            return self.eval(e.a) if truthy(self.eval(e.test)) else self.eval(e.b)
        if isinstance(e, FStr):
            out = "".join(p if isinstance(p, str) else BUILTINS["str"](self.lim, self.eval(p)) for p in e.parts)
            return guard(out, self.lim)
        if isinstance(e, Call):
            args = [self.eval(a) for a in e.args]
            kwargs = {k: self.eval(v) for k, v in e.kwargs}
            if e.func == "fail":
                msg = " ".join(BUILTINS["str"](self.lim, a) for a in args) or "the script called fail()"
                raise JigError("E_SCRIPT", f"fail(): {msg}")
            if e.func == "print":
                line = " ".join(BUILTINS["str"](self.lim, a) for a in args)
                self.log.append(line)
                if self.on_log:
                    self.on_log(line)
                return None
            try:
                return guard(BUILTINS[e.func](self.lim, *args, **kwargs), self.lim)
            except TypeError as ex:
                raise fail(f"{e.func}(): wrong arguments ({ex})") from None
        if isinstance(e, Method):
            base = self.eval(e.base)
            if isinstance(base, Bound):
                raise fail(f"'{base.name}' is a command result; use {base.name}.output.<field>")
            return call_method(self.lim, base, e.name, [self.eval(a) for a in e.args])
        raise fail(f"cannot evaluate {type(e).__name__}")

    def index(self, base: Any, key: Any) -> Any:
        if isinstance(base, Bound):
            base = base.view()
        if isinstance(base, dict):
            if isinstance(key, (list, dict, set)):
                raise fail(f"map key must be a string, number, bool or null, got {type_name(key)}")
            if key not in base:
                raise JigError("E_PARAM", f"map has no key {key!r} (available: {sorted(map(str, base))})")
            return base[key]
        if isinstance(base, (list, str)):
            if not isinstance(key, int) or isinstance(key, bool):
                raise fail(f"{type_name(base)} index must be an integer, got {type_name(key)}")
            if not -len(base) <= key < len(base):
                raise fail(f"index {key} is out of range for a {type_name(base)} of {len(base)}")
            return base[key]
        raise fail(f"cannot index a {type_name(base)}")

    def binop(self, op: str, a: Any, b: Any) -> Any:
        if op == "+":
            if _num(a) and _num(b):
                return guard(a + b, self.lim)
            if isinstance(a, str) and isinstance(b, str) or isinstance(a, list) and isinstance(b, list):
                precheck(len(a) + len(b), self.lim)
                return a + b
            raise fail(f"cannot add {type_name(a)} and {type_name(b)}"
                       + (" (use str() or an f-string to join text and numbers)" if str in (type(a), type(b)) else ""))
        if op == "*":
            if _num(a) and _num(b):
                return guard(a * b, self.lim)
            seq, n = (a, b) if isinstance(a, (str, list)) else (b, a)
            if isinstance(seq, (str, list)) and isinstance(n, int) and not isinstance(n, bool):
                precheck(len(seq) * max(n, 0), self.lim)
                return seq * n
            raise fail(f"cannot multiply {type_name(a)} and {type_name(b)}")
        if not (_num(a) and _num(b)):
            raise fail(f"'{op}' needs numbers, got {type_name(a)} and {type_name(b)}")
        if op in ("/", "//", "%") and b == 0:
            raise fail("division by zero")
        if op == "-":
            return guard(a - b, self.lim)
        return guard(a / b if op == "/" else a // b if op == "//" else a % b, self.lim)

    def compare(self, op: str, a: Any, b: Any) -> bool:
        if op in ("is", "is not"):
            if b is not None and a is not None:
                raise fail("'is' only compares with null/None; use ==")
            return (a is b) == (op == "is")
        if op in ("in", "not in"):
            if isinstance(b, str):
                if not isinstance(a, str):
                    raise fail(f"'in' on a string needs a string, got {type_name(a)}")
                r = a in b
            elif isinstance(b, (list, dict, set, Queue)):
                try:
                    r = a in b
                except TypeError:
                    raise fail(f"a {type_name(a)} cannot be a key of a {type_name(b)}") from None
            else:
                raise fail(f"'in' needs a list, map, queue, set or string, got {type_name(b)}")
            return r == (op == "in")
        if isinstance(a, Bound) or isinstance(b, Bound):
            raise fail("compare a command result's fields (x.status, x.output.<field>), not the result itself")
        if op == "==":
            return a == b
        if op == "!=":
            return a != b
        if not ((_num(a) and _num(b)) or (isinstance(a, str) and isinstance(b, str))
                or (isinstance(a, list) and isinstance(b, list))):
            raise fail(f"cannot compare {type_name(a)} {op} {type_name(b)}")
        try:
            return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
        except TypeError:
            raise fail(f"cannot compare {type_name(a)} {op} {type_name(b)}") from None


def run_script(rt: Runtime, source: str, replace: bool = False, continue_on_error: bool = False,
               on_start: Callable[[Statement], None] | None = None,
               on_result: Callable[[Statement, dict], None] | None = None,
               variables: dict[str, Any] | None = None, resume: bool = False,
               on_log: Callable[[str], None] | None = None, script_id: str = "inline") -> dict:
    variables = dict(variables or {})
    try:
        stmts = parse(source, set(rt.commands), predefined=set(variables))
    except ParseError as e:
        return {"status": "failed", "error": {"code": "E_PARSE", "message": str(e)}, "results": []}
    calls = [s for s in walk(stmts) if isinstance(s, Statement)]
    top = [s for s in stmts if isinstance(s, Statement)]
    try:
        planned = plan_bindings(rt, top, replace, variables, allow_existing=resume)
        nested = [s for s in calls if s not in top and rt.commands[s.command]["artifact"] == "create"]
        for s in nested:
            aid = _explicit_id(s, variables)
            if aid and rt.store.exists(aid) and not (replace or resume):
                raise JigError("E_ARTIFACT_EXISTS", f"line {s.line} creates {aid}, which already exists. Use "
                                                        f"--replace to start over or --resume to continue it")
    except JigError as e:
        return {"status": "failed", "error": e.to_dict(), "results": []}
    bindings = {id(top[i]): aid for i, aid in planned.items()}
    it = Interp(rt, variables, replace=replace, resume=resume, continue_on_error=continue_on_error,
                on_start=on_start, on_result=on_result, on_log=on_log, bindings=bindings, script_id=script_id)
    outer_flags = rt.script_flags
    if rt.script_depth == 0:     # scripts called as steps (script commands) inherit --replace / --resume
        rt.script_flags = {"replace": replace, "resume": resume}
    try:
        it.run(stmts)
    finally:
        rt.script_flags = outer_flags
    out = {"status": it.status,
           "bindings": {top[i].source.split("(")[0] + f"@{top[i].line}": a for i, a in planned.items()},
           "executed": len([r for r in it.results if r["result"].get("command")]), "total": len(calls),
           "step_failures": it.step_failures, "results": it.results, "log": it.log}
    if it.error:
        out["error"] = it.error
    if "result" in it.vars:      # what a script hands back when it runs as a step (a script command)
        try:
            out["result"] = to_data(it.vars["result"])
        except JigError as e:
            out["status"] = "failed"
            out["error"] = {"code": "E_SCRIPT", "message": f"result: {e.message}"}
    return out


def _already_completed(rt: Runtime, command: str, target: Any, kwargs: dict, context: dict) -> dict | None:
    """--resume for runs made before step journals existed: the stored result if this exact step
    already completed for its artifact."""
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
    except JigError:
        return None
    if st.get("params") is not None and st["params"] != params:
        return None  # inputs changed: run it again
    return {"command": command, "status": "completed", "skipped": True, "artifact_id": aid,
            "output": rt.store.stage_output(aid, command), "validation": {"passed": True, "findings": []},
            "execution": {"model": None, "duration_ms": None, "token_usage": None, "cost_usd": None,
                          "run_id": st["run_id"], "note": "resumed: stage already completed"},
            "error": None}
