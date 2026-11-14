"""Offline check of a Jig script: parses it and checks every command call's parameter names.

Never calls an agent and costs nothing.

    py .claude/skills/jig-script/check.py factory/pong-factory.jig
    py .claude/skills/jig-script/check.py pipeline.jig --var id --var goal     # names a batch row supplies
    py .claude/skills/jig-script/check.py pipeline.jig --vars-file vars.json   # names from a --vars file
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--project", default=".")
    ap.add_argument("--var", action="append", default=[], help="variable supplied from outside (repeatable)")
    ap.add_argument("--vars-file", help="JSON or YAML file whose top-level keys are variables, or a batch "
                                        "items file (list of rows)")
    a = ap.parse_args()
    project = Path(a.project).resolve()
    sys.path.insert(0, str(project))
    from jig.loader import load_commands
    from jig.parser import ParseError, Statement, parse, walk

    names = set(a.var)
    if a.vars_file:
        import yaml
        data = yaml.safe_load(Path(a.vars_file).read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else [data]
        for row in rows:
            names |= set(row or {})

    cmds = load_commands(project)
    src = Path(a.script).read_text(encoding="utf-8")
    try:
        stmts = parse(src, set(cmds), predefined=names)
    except ParseError as e:
        print(f"E_PARSE: {e}")
        return 1

    problems = []
    calls = [s for s in walk(stmts) if isinstance(s, Statement)]
    for s in calls:
        c = cmds[s.command]
        allowed = set(c["parameters"])
        for k in s.kwargs:
            if k not in allowed:
                problems.append(f"line {s.line}: {s.command}() has no parameter '{k}' "
                                f"(has: {', '.join(sorted(allowed)) or 'none'})")
        tgt = c["target"]
        if tgt.get("required") and tgt.get("type") != "none" and s.target is None:
            problems.append(f"line {s.line}: {s.command}() needs a target")
    for p in problems:
        print(p)
    steps = ", ".join(f"{s.command}@{s.line}" for s in calls)
    print(f"{'FAILED' if problems else 'OK'}: {len(calls)} command call(s): {steps or 'none'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
