"""Run one script for many items in parallel.

Items file (YAML list). Each item is a set of variables for the script; `id` is required
and names the item (for app pipelines it is usually also the artifact id):

    - {id: TODO-001, goal: "Todo list app", stack: [React], standard: simple}
    - {id: NOTE-001, goal: "Notes app",     stack: [React], standard: simple}

Each item runs as its own `jig run` process, so items are fully isolated; the
store's file locks make the shared files safe. Results land in
.jig/batches/<name>/items/<id>.json and summary.json. --resume skips items that
already completed and resumes the others step by step.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

import yaml

from .store import now_iso, read_json, write_json


def load_items(path: Path) -> list[dict]:
    items = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
        raise ValueError("items file must be a YAML list of mappings")
    ids = [i.get("id") for i in items]
    if any(not isinstance(x, str) or not x for x in ids):
        raise ValueError("every item needs a non-empty string `id`")
    if len(set(ids)) != len(ids):
        raise ValueError("item ids must be unique")
    return items


def _summarize(out: dict | None, code: int, stderr: str) -> dict:
    if out is None:
        return {"status": "failed", "error": f"runner exited {code}: {stderr[-500:]}", "steps": [], "cost_usd": None}
    steps = []
    cost = 0.0
    have_cost = False
    for r in out.get("results", []):
        res = r["result"]
        c = (res.get("execution") or {}).get("cost_usd")
        if c is not None:
            cost += c
            have_cost = True
        steps.append({"line": r["line"], "command": res.get("command"), "status": res.get("status"),
                      "skipped": bool(res.get("skipped")), "artifact_id": res.get("artifact_id"),
                      "error": (res.get("error") or {}).get("message")})
    failed = next((s for s in steps if s["status"] != "completed"), None)
    return {"status": out.get("status"), "steps": steps, "executed": out.get("executed"), "total": out.get("total"),
            "failed_at": failed["command"] if failed else None,
            "error": (failed or {}).get("error") or (out.get("error") or {}).get("message"),
            "cost_usd": round(cost, 4) if have_cost else None}


def run_batch(project: Path, items_file: Path, script: Path, parallel: int = 3, resume: bool = False,
              sandbox: str | None = None, echo: Callable[[str], None] = print, jig_cmd: list[str] | None = None) -> dict:
    items = load_items(items_file)
    name = items_file.stem
    bdir = project / ".jig" / "batches" / name
    (bdir / "items").mkdir(parents=True, exist_ok=True)
    cmd = jig_cmd or [sys.executable, "-m", "jig"]
    started = time.monotonic()

    def work(item: dict) -> dict:
        iid = item["id"]
        rec_path = bdir / "items" / f"{iid}.json"
        prev = read_json(rec_path)
        if resume and prev and prev.get("status") == "completed":
            echo(f"[skip] {iid}: already completed")
            return {**prev, "skipped": True}
        vars_path = bdir / "items" / f"{iid}.vars.json"
        write_json(vars_path, item)
        argv = [*cmd, "--project", str(project), "run", str(script), "--vars", str(vars_path), "--json"]
        if resume:
            argv.append("--resume")
        if sandbox:
            argv += ["--sandbox", sandbox]
        echo(f"[start] {iid}")
        t0 = time.monotonic()
        p = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           stdin=subprocess.DEVNULL)
        (bdir / "items" / f"{iid}.stderr.log").write_text(p.stderr, encoding="utf-8")
        try:
            out = json.loads(p.stdout)
        except json.JSONDecodeError:
            out = None
        rec = {"id": iid, "vars": item, **_summarize(out, p.returncode, p.stderr),
               "wall_s": round(time.monotonic() - t0, 1), "finished_at": now_iso()}
        write_json(rec_path, rec)
        write_json(bdir / "items" / f"{iid}.result.json", out)
        echo(f"[{'done' if rec['status'] == 'completed' else 'FAIL'}] {iid}: {rec['status']}"
             + (f" at {rec['failed_at']}: {rec['error']}" if rec.get("failed_at") else "")
             + f" ({rec['wall_s']}s)")
        return rec

    with ThreadPoolExecutor(max_workers=max(1, parallel)) as pool:
        records = list(pool.map(work, items))
    summary = {"batch": name, "script": str(script), "items_file": str(items_file), "parallel": parallel,
               "sandbox": sandbox or "none",
               "finished_at": now_iso(), "wall_s": round(time.monotonic() - started, 1),
               "completed": sum(r["status"] == "completed" for r in records), "total": len(records),
               "items": [{k: r.get(k) for k in ("id", "status", "failed_at", "error", "cost_usd", "wall_s", "skipped")}
                         for r in records]}
    write_json(bdir / "summary.json", summary)
    return summary


def format_summary(s: dict) -> str:
    lines = [f"batch {s['batch']}: {s['completed']}/{s['total']} completed in {s['wall_s']}s "
             f"(parallel={s['parallel']})", ""]
    w = max([len(i["id"]) for i in s["items"]] + [4])
    lines.append(f"{'ITEM':<{w}}  {'STATUS':<10} {'TIME':>7}  {'COST*':>7}  DETAIL")
    for i in s["items"]:
        detail = "skipped (already completed)" if i.get("skipped") else \
            (f"failed at {i['failed_at']}: {i['error']}" if i.get("failed_at") else "")
        cost = f"${i['cost_usd']:.2f}" if i.get("cost_usd") is not None else "-"
        lines.append(f"{i['id']:<{w}}  {i['status']:<10} {str(i.get('wall_s', '')) + 's':>7}  {cost:>7}  {detail[:110]}")
    lines += ["", "* cost as reported by Claude Code (on a subscription this is usage, not a charge)"]
    return "\n".join(lines)
