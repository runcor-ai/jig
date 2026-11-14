"""jig CLI: run scripts and single commands, run batches, inspect commands and artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .errors import ERROR_CODES
from .loader import CommandDefError, command_dirs, load_commands
from .parser import ParseError, Statement, parse
from .script import run_script
from .store import read_json


def _rt(args):
    from .runtime import Runtime
    echo = None if getattr(args, "json", False) else (lambda m: print(m, flush=True))
    return Runtime(Path(args.project), echo=echo, sandbox=getattr(args, "sandbox", None))


def _fmt_result(res: dict) -> str:
    ex = res.get("execution") or {}
    bits = [f"status={res['status']}"]
    if res.get("skipped"):
        bits.append("(resumed: already completed)")
    if res.get("artifact_id"):
        bits.append(f"artifact={res['artifact_id']}")
    v = res.get("validation") or {}
    if v:
        errs = sum(1 for f in v.get("findings", []) if f["severity"] == "error")
        warns = sum(1 for f in v.get("findings", []) if f["severity"] == "warning")
        bits.append(f"validation={'passed' if v.get('passed') else 'FAILED'} ({errs} errors, {warns} warnings)")
    for key, label in (("model", "model"), ("attempts", "attempts"), ("sandbox", "sandbox")):
        if ex.get(key):
            bits.append(f"{label}={ex[key]}")
    if ex.get("duration_ms_wall") is not None:
        bits.append(f"wall_ms={ex['duration_ms_wall']}")
    if ex.get("cost_usd") is not None:
        bits.append(f"reported_cost=${ex['cost_usd']:.4f}")
    if ex.get("permission_denials"):
        bits.append(f"permission_denials={len(ex['permission_denials'])}")
    lines = ["  " + "  ".join(bits)]
    if res.get("error"):
        lines.append(f"  error: {res['error']['code']}: {res['error']['message']}")
    for f in (v.get("findings") or [])[:12]:
        lines.append(f"  - [{f['severity']}] {f['rule']}: {f['message']}")
    if len(v.get("findings") or []) > 12:
        lines.append(f"  ... {len(v['findings']) - 12} more findings")
    return "\n".join(lines)


def cmd_run(args):
    rt = _rt(args)
    source = Path(args.script).read_text(encoding="utf-8")
    on_start = None if args.json else (lambda st: print(f"\n> line {st.line}: {st.source.splitlines()[0]}"
                                                        f"{' ...' if chr(10) in st.source else ''}", flush=True))
    on_result = None if args.json else (lambda st, res: print(_fmt_result(res), flush=True))
    variables = json.loads(Path(args.vars).read_text(encoding="utf-8")) if args.vars else {}
    for kv in args.var or []:
        k, _, v = kv.partition("=")
        variables[k] = v
    on_log = None if args.json else (lambda line: print(f"  | {line}", flush=True))
    script_path = Path(args.script).resolve()
    try:
        script_id = script_path.relative_to(rt.project_dir).as_posix()
    except ValueError:
        script_id = script_path.as_posix()
    out = run_script(rt, source, replace=args.replace, continue_on_error=args.continue_on_error,
                     on_start=on_start, on_result=on_result, variables=variables, resume=args.resume,
                     on_log=on_log, script_id=script_id)
    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        if out.get("error"):
            print(f"error: {out['error']['code']}: {out['error']['message']}")
        print(f"\nscript {out['status']}: {out.get('executed', 0)} command step(s) run "
              f"({out.get('total', 0)} command call(s) in the script)")
    return 0 if out["status"] == "completed" else 1


def cmd_exec(args):
    rt = _rt(args)
    try:
        stmts = parse(args.statement, set(rt.commands))
    except ParseError as e:
        print(f"E_PARSE: {e}")
        return 2
    if len(stmts) != 1 or not isinstance(stmts[0], Statement) or stmts[0].bind:
        print("exec takes exactly one statement without assignment; use `jig run` for scripts")
        return 2
    st = stmts[0]
    res = rt.execute(rt.normalize(st.command, st.target, st.kwargs))
    print(json.dumps(res, indent=2, default=str) if args.json else _fmt_result(res))
    return 0 if res["status"] == "completed" else 1


def cmd_status(args):
    rt = _rt(args)
    if args.artifact:
        if not rt.store.exists(args.artifact):
            print(f"no artifact '{args.artifact}'")
            return 1
        m = rt.store.manifest(args.artifact)
        out = {"id": m["id"], "title": m["title"], "workspace": m.get("workspace"),
               "stages": {k: v["status"] for k, v in m["stages"].items()}, "history": m["history"][-10:]}
    else:
        out = {"artifacts": {a: {k: v["status"] for k, v in rt.store.manifest(a)["stages"].items()}
                             for a in rt.store.list_ids()},
               "running": rt.store.running()}
    print(json.dumps(out, indent=2, default=str))
    return 0


def cmd_show(args):
    rt = _rt(args)
    m = rt.store.manifest(args.artifact)
    if not args.stage:
        print(json.dumps(m, indent=2))
        return 0
    st = m["stages"].get(args.stage)
    if not st:
        print(f"no stage '{args.stage}'; stages: {list(m['stages'])}")
        return 1
    print(json.dumps(read_json(rt.store.root / st["file"]), indent=2))
    return 0


def cmd_commands(args):
    cmds = load_commands(Path(args.project))
    if args.json:
        print(json.dumps({n: {**c.spec, "source": c.source, "path": str(c.path)} for n, c in cmds.items()},
                         indent=2, default=str))
        return 0
    print(f"{len(cmds)} commands loaded\n")
    for name, c in sorted(cmds.items()):
        params = ", ".join(c["parameters"]) or "-"
        pol = c["tool_policy"] if isinstance(c["tool_policy"], str) else "inline"
        over = f"  (overrides {c.overrides})" if c.overrides else ""
        print(f"  {name:<12} [{c.source}]{over} {c['purpose']}\n"
              f"               params: {params}; requires: {c['requires'] or '-'}; "
              f"tools: {pol if c['mode'] == 'agent' else 'none (runs in Jig)'}")
    print("\nsearched: " + "; ".join(f"{s}={d}{'' if d.is_dir() else ' (missing)'}"
                                     for s, d in command_dirs(Path(args.project))))
    return 0


def cmd_check(args):
    ok_all = True
    try:
        cmds = load_commands(Path(args.project))
        by = {}
        for c in cmds.values():
            by[c.source] = by.get(c.source, 0) + 1
        print(f"commands: {len(cmds)} loaded OK ({', '.join(f'{k} {v}' for k, v in sorted(by.items()))})")
    except CommandDefError as e:
        print(f"commands: INVALID\n{e}")
        return 1
    rt = _rt(args)
    for c in cmds.values():  # every named tool policy must exist
        if c["mode"] == "agent":
            try:
                rt.tool_policy(c)
            except Exception as e:
                print(f"  {c.name}: {e}")
                ok_all = False
    ok, why = rt.adapter.available()
    ok_all &= ok
    print(f"agent adapter {rt.adapter.name}: {'available' if ok else 'UNAVAILABLE'} ({why})")
    from .sandbox import DockerSandbox
    ok2, why2 = DockerSandbox().check()
    print(f"sandbox docker: {'ready' if ok2 else 'not ready'} ({why2})")
    return 0 if ok_all else 1


def cmd_sandbox_build(args):
    from .sandbox import IMAGE, build_image
    print(f"building {IMAGE} ...")
    return build_image()


def cmd_batch(args):
    from .batch import format_summary, run_batch
    s = run_batch(Path(args.project).resolve(), Path(args.items), Path(args.script), parallel=args.parallel,
                  resume=args.resume, sandbox=args.sandbox, echo=lambda m: print(m, flush=True))
    print()
    print(format_summary(s))
    return 0 if s["completed"] == s["total"] else 1


def cmd_batch_status(args):
    from .batch import format_summary
    s = read_json(Path(args.project) / ".jig" / "batches" / args.name / "summary.json")
    if not s:
        print(f"no finished batch named '{args.name}'")
        return 1
    print(format_summary(s))
    return 0


def _sandbox_arg(p):
    p.add_argument("--sandbox", choices=["none", "docker"], default=None,
                   help="docker: run agents and test commands in a throwaway container with only the workspace mounted")


def main(argv=None):
    p = argparse.ArgumentParser(prog="jig", description="Jig: a scripting language for LLM agents")
    p.add_argument("--project", default=".", help="project directory (jig.yaml, commands/, .jig/)")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run a .jig script")
    r.add_argument("script")
    r.add_argument("--replace", action="store_true", help="archive existing artifacts the script re-creates")
    r.add_argument("--continue-on-error", action="store_true")
    r.add_argument("--resume", action="store_true", help="skip steps that already completed with the same inputs")
    r.add_argument("--vars", help="JSON file of variables available to the script")
    r.add_argument("--var", action="append", help="name=value variable (repeatable)")
    r.add_argument("--json", action="store_true")
    _sandbox_arg(r)
    r.set_defaults(fn=cmd_run)

    e = sub.add_parser("exec", help="execute one statement, e.g. jig exec 'research(\"passkeys\")'")
    e.add_argument("statement")
    e.add_argument("--json", action="store_true")
    _sandbox_arg(e)
    e.set_defaults(fn=cmd_exec)

    bt = sub.add_parser("batch", help="run one script for every item in a YAML list, in parallel")
    bt.add_argument("items", help="YAML list of items; each needs an id")
    bt.add_argument("--script", required=True)
    bt.add_argument("--parallel", type=int, default=3)
    bt.add_argument("--resume", action="store_true", help="skip completed items, resume the rest")
    _sandbox_arg(bt)
    bt.set_defaults(fn=cmd_batch)

    bs = sub.add_parser("batch-status", help="show the summary of a finished batch")
    bs.add_argument("name", help="batch name (the items file name without extension)")
    bs.set_defaults(fn=cmd_batch_status)

    s = sub.add_parser("status", help="stages of one artifact, or all artifacts and running commands")
    s.add_argument("artifact", nargs="?")
    s.set_defaults(fn=cmd_status)

    sh = sub.add_parser("show", help="print an artifact manifest or a stage record")
    sh.add_argument("artifact")
    sh.add_argument("stage", nargs="?")
    sh.set_defaults(fn=cmd_show)

    c = sub.add_parser("commands", help="list loaded commands (built-in, user, project)")
    c.add_argument("--json", action="store_true")
    c.set_defaults(fn=cmd_commands)

    sub.add_parser("check", help="validate command definitions; check agent and sandbox").set_defaults(fn=cmd_check)
    sub.add_parser("sandbox-build", help="build the docker image used by --sandbox docker").set_defaults(
        fn=cmd_sandbox_build)
    sub.add_parser("errors", help="list error codes").set_defaults(
        fn=lambda a: print("\n".join(f"{k:<22}{v}" for k, v in ERROR_CODES.items())) or 0)

    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        return args.fn(args)
    except CommandDefError as e:
        print(f"E_COMMAND_DEF: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
