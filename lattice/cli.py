"""lattice CLI: run scripts and individual commands, inspect artifacts, approve, benchmark."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_registry
from .errors import ERROR_CODES
from .parser import ParseError, parse
from .procedures import docker_available
from .script import run_script
from .store import read_json


def _rt(args, interactive=False):
    from .runtime import Runtime
    echo = None if getattr(args, "json", False) else (lambda m: print(m, flush=True))
    return Runtime(Path(args.project), interactive=interactive, echo=echo)


def _fmt_result(res: dict) -> str:
    ex = res.get("execution") or {}
    bits = [f"status={res['status']}"]
    if res.get("artifact_id"):
        bits.append(f"artifact={res['artifact_id']}")
    v = res.get("validation") or {}
    if v:
        errs = sum(1 for f in v.get("findings", []) if f["severity"] == "error")
        warns = sum(1 for f in v.get("findings", []) if f["severity"] == "warning")
        bits.append(f"validation={'passed' if v.get('passed') else 'FAILED'} ({errs} errors, {warns} warnings)")
    if ex.get("model"):
        bits.append(f"model={ex['model']}")
    if ex.get("attempts"):
        bits.append(f"attempts={ex['attempts']}")
    if ex.get("duration_ms") is not None:
        bits.append(f"agent_ms={ex['duration_ms']}")
    if ex.get("duration_ms_wall") is not None:
        bits.append(f"wall_ms={ex['duration_ms_wall']}")
    if ex.get("cost_usd") is not None:
        bits.append(f"cost=${ex['cost_usd']:.4f}")
    if ex.get("token_usage"):
        tu = ex["token_usage"]
        bits.append(f"tokens(in={tu.get('input_tokens', 0)}+cache_r={tu.get('cache_read_input_tokens', 0)}"
                    f"+cache_w={tu.get('cache_creation_input_tokens', 0)}, out={tu.get('output_tokens', 0)})")
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
    out = run_script(rt, source, replace=args.replace, continue_on_error=args.continue_on_error,
                     on_start=on_start, on_result=on_result, variables=variables, resume=args.resume)
    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        if out.get("error"):
            print(f"error: {out['error']['code']}: {out['error']['message']}")
        print(f"\nscript {out['status']}: {out.get('executed', 0)}/{out.get('total', 0)} statements executed")
    return 0 if out["status"] == "completed" else 1


def cmd_exec(args):
    rt = _rt(args, interactive=True)
    try:
        stmts = parse(args.statement, set(rt.registry.commands))
    except ParseError as e:
        print(f"E_PARSE: {e}")
        return 2
    if len(stmts) != 1:
        print("exec takes exactly one statement; use `lattice run` for scripts")
        return 2
    st = stmts[0]
    res = rt.execute(rt.normalize(st.command, st.target, st.kwargs))
    print(json.dumps(res, indent=2, default=str) if args.json else _fmt_result(res))
    return 0 if res["status"] == "completed" else 1


def cmd_status(args):
    rt = _rt(args)
    res = rt.run("status", args.artifact)
    print(json.dumps(res["output"] if res["status"] == "completed" else res, indent=2, default=str))
    return 0 if res["status"] == "completed" else 1


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
    reg = load_registry()
    if args.json:
        print(json.dumps(reg.commands, indent=2))
        return 0
    print(f"Lattice command registry v{reg.version}: {len(reg.commands)} commands")
    cur = None
    for name, s in sorted(reg.commands.items(), key=lambda kv: (kv[1]["category"], kv[0])):
        if s["category"] != cur:
            cur = s["category"]
            print(f"\n{cur}")
        params = ", ".join(s["parameters"]) or "-"
        print(f"  {name:<12} [{s['maturity']:<11}] {s['purpose']}\n               params: {params}; "
              f"requires: {s['requires'] or '-'}; schema: {s['output_schema']}; "
              f"tools: {s['execution'].get('tool_policy', s['execution']['mode'])}")
    return 0


def cmd_approve(args):
    rt = _rt(args, interactive=True)
    res = rt.run("approve", args.artifact, command=args.command, note=args.note)
    print(_fmt_result(res))
    return 0 if res["status"] == "completed" else 1


def cmd_check(args):
    reg = load_registry()
    print(f"registry v{reg.version}: {len(reg.commands)} commands, {len(reg.profiles)} profiles, "
          f"{len(reg.stacks)} stacks, {len(reg.decision_models)} decision models - OK")
    rt = _rt(args)
    ok, why = rt.adapter.available()
    print(f"agent adapter {rt.adapter.name}: {'available' if ok else 'UNAVAILABLE'} ({why})")
    ok2, why2 = docker_available()
    print(f"docker: {'available' if ok2 else 'UNAVAILABLE'} ({why2})")
    return 0 if ok else 1


def cmd_batch(args):
    from .batch import format_summary, run_batch
    s = run_batch(Path(args.project).resolve(), Path(args.items), Path(args.script), parallel=args.parallel,
                  resume=args.resume, echo=lambda m: print(m, flush=True))
    print()
    print(format_summary(s))
    return 0 if s["completed"] == s["total"] else 1


def cmd_batch_status(args):
    from .batch import format_summary
    s = read_json(Path(args.project) / ".lattice" / "batches" / args.name / "summary.json")
    if not s:
        print(f"no finished batch named '{args.name}'")
        return 1
    print(format_summary(s))
    return 0


def cmd_bench(args):
    from .bench import run_bench
    out = run_bench(Path(args.project), Path(args.suite), runs=args.runs, modes=args.mode)
    print(json.dumps(out["summary"], indent=2))
    print(f"\nresults: {out['path']}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="lattice", description="Lattice v0.1 command runtime")
    p.add_argument("--project", default=".", help="project directory (holds lattice.yaml and .lattice/)")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run a Lattice script")
    r.add_argument("script")
    r.add_argument("--replace", action="store_true", help="archive existing artifacts the script re-creates")
    r.add_argument("--continue-on-error", action="store_true")
    r.add_argument("--resume", action="store_true", help="skip steps that already completed with the same inputs")
    r.add_argument("--vars", help="JSON file of variables available to the script")
    r.add_argument("--var", action="append", help="name=value variable (repeatable)")
    r.add_argument("--json", action="store_true")
    r.set_defaults(fn=cmd_run)

    e = sub.add_parser("exec", help="execute one command, e.g. lattice exec 'status(\"CRM-001\")'")
    e.add_argument("statement")
    e.add_argument("--json", action="store_true")
    e.set_defaults(fn=cmd_exec)

    s = sub.add_parser("status", help="artifact status, or all artifacts and running commands")
    s.add_argument("artifact", nargs="?")
    s.set_defaults(fn=cmd_status)

    sh = sub.add_parser("show", help="print an artifact manifest or a stage record")
    sh.add_argument("artifact")
    sh.add_argument("stage", nargs="?")
    sh.set_defaults(fn=cmd_show)

    c = sub.add_parser("commands", help="list the command registry")
    c.add_argument("--json", action="store_true")
    c.set_defaults(fn=cmd_commands)

    a = sub.add_parser("approve", help="grant a single-use approval (interactive confirmation)")
    a.add_argument("artifact")
    a.add_argument("command")
    a.add_argument("--note")
    a.set_defaults(fn=cmd_approve)

    bt = sub.add_parser("batch", help="run one script for every item in a YAML list, in parallel")
    bt.add_argument("items", help="YAML list of items; each needs an id")
    bt.add_argument("--script", required=True)
    bt.add_argument("--parallel", type=int, default=3)
    bt.add_argument("--resume", action="store_true", help="skip completed items, resume the rest")
    bt.set_defaults(fn=cmd_batch)

    bs = sub.add_parser("batch-status", help="show the summary of a finished batch")
    bs.add_argument("name", help="batch name (the items file name without extension)")
    bs.set_defaults(fn=cmd_batch_status)

    k = sub.add_parser("check", help="validate the registry and check agent/docker availability")
    k.set_defaults(fn=cmd_check)

    b = sub.add_parser("bench", help="run a reliability benchmark suite")
    b.add_argument("suite")
    b.add_argument("--runs", type=int, default=3)
    b.add_argument("--mode", nargs="+", default=["baseline", "lattice"], choices=["baseline", "lattice"])
    b.set_defaults(fn=cmd_bench)

    sub.add_parser("errors", help="list error codes").set_defaults(
        fn=lambda a: print("\n".join(f"{k:<22}{v}" for k, v in ERROR_CODES.items())) or 0)

    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
