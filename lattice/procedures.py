"""Procedures run by the runtime itself (no agent): the test runner and native control commands."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .errors import LatticeError
from .store import now_iso, read_json, write_json
from .validators import SKIP_DIRS

if TYPE_CHECKING:
    from .runtime import ExecContext, Runtime


# ── test runner ─────────────────────────────────────────────────────────
def docker_available() -> tuple[bool, str]:
    exe = shutil.which("docker")
    if not exe:
        return False, "docker CLI not found on PATH"
    try:
        p = subprocess.run([exe, "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return False, "docker info timed out"
    if p.returncode != 0:
        return False, f"docker daemon not reachable: {p.stderr.strip()[:300]}"
    return True, p.stdout.strip()


def _run(cmd: list[str], cwd: Path, timeout: int, log: Path, env: dict | None = None) -> tuple[int | None, int, str]:
    start = time.monotonic()
    import os
    cmd = list(cmd)
    exe = shutil.which(cmd[0])  # resolves npm -> npm.cmd on Windows
    if exe:
        cmd[0] = exe
    with open(log, "a", encoding="utf-8", errors="replace") as lf:
        lf.write(f"\n$ {' '.join(cmd)}   (cwd={cwd}, {now_iso()}, env={env or {}})\n")
        lf.flush()
        try:
            p = subprocess.run(cmd, cwd=str(cwd), stdout=lf, stderr=subprocess.STDOUT, timeout=timeout,
                               stdin=subprocess.DEVNULL, env={**os.environ, **(env or {})})
            code = p.returncode
        except subprocess.TimeoutExpired:
            lf.write(f"\n[lattice] TIMEOUT after {timeout}s\n")
            code = None
        except FileNotFoundError as e:
            lf.write(f"\n[lattice] command not found: {e}\n")
            code = 127
    elapsed = int((time.monotonic() - start) * 1000)
    tail = log.read_text(encoding="utf-8", errors="replace")[-3000:]
    return code, elapsed, tail


def parse_junit(files: list[Path]) -> dict:
    tests = failures = errors = skipped = 0
    cases, failed = [], []
    for f in files:
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError as e:
            failed.append({"name": f.name, "kind": "report_parse_error", "message": str(e)})
            errors += 1
            continue
        for tc in root.iter("testcase"):
            name = ".".join(x for x in [tc.get("classname"), tc.get("name")] if x)
            tests += 1
            cases.append(name)
            if tc.find("skipped") is not None:
                skipped += 1
            for kind in ("failure", "error"):
                el = tc.find(kind)
                if el is not None:
                    if kind == "failure":
                        failures += 1
                    else:
                        errors += 1
                    msg = (el.get("message") or el.text or "").strip()
                    failed.append({"name": name, "kind": kind, "message": msg[:1500]})
    return {"tests": tests, "failures": failures, "errors": errors, "skipped": skipped,
            "case_names": cases, "failed_cases": failed}


def _http(url: str, timeout: int = 10) -> tuple[int | None, str]:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=timeout) as r:
            return r.status, ""
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # connection refused etc.
        return None, str(e)[:200]


def _safe_clean(ws: Path, rel: str) -> None:
    target = (ws / rel).resolve()
    target.relative_to(ws.resolve())  # raises if outside workspace
    if target.is_dir():
        shutil.rmtree(target)


def run_test_suites(rt: "Runtime", ctx: "ExecContext") -> dict:
    stack = ctx.stack or {}
    suites = stack.get("test_suites") or []
    if not suites:
        raise LatticeError("E_UNAVAILABLE", f"stack profile '{stack.get('name')}' defines no test suites")
    wanted = ctx.params.get("suites") or []
    unknown = [w for w in wanted if w not in {s["name"] for s in suites}]
    if unknown:
        raise LatticeError("E_PARAM", f"unknown suites {unknown}; available: {[s['name'] for s in suites]}")
    if wanted:
        suites = [s for s in suites if s["name"] in wanted]
    needs_docker = any("docker" in Path(str((s.get("command") or s.get("setup") or [""])[0])).name.lower()
                       for s in suites)
    why = "not required"
    if needs_docker:
        ok, why = docker_available()
        if not ok:
            raise LatticeError("E_UNAVAILABLE", f"cannot run test suites: {why}")
    env = ctx.env()
    ports = {k: v for k, v in ((ctx.manifest or {}).get("ports") or {}).items()}
    ws = ctx.workspace
    results, case_names, failed_cases = [], [], []
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for s in suites:
        log = ctx.run_dir / f"test-{s['name']}.log"
        rt.progress(ctx, f"suite {s['name']} running")
        if s["type"] == "junit":
            for rel in s.get("clean", []):
                _safe_clean(ws, rel)
            for pre in s.get("prepare", []):
                _run(pre, ws, int(s.get("timeout_s", 1800)), log, env)
            code, ms, tail = _run(s["command"], ws, int(s.get("timeout_s", 1800)), log, env)
            files = sorted({p for g in s.get("reports", []) for p in ws.glob(g)})
            parsed = parse_junit(files)
            if code is None:
                status = "error"
            elif parsed["tests"] == 0:
                status = "error"
            elif parsed["failures"] or parsed["errors"] or code != 0:
                status = "failed"
            else:
                status = "passed"
            for k in totals:
                totals[k] += parsed[k]
            case_names += parsed["case_names"]
            failed_cases += [{**c, "suite": s["name"]} for c in parsed["failed_cases"]]
            results.append({"name": s["name"], "type": "junit", "status": status, "exit_code": code,
                            "duration_ms": ms, "tests": parsed["tests"], "failures": parsed["failures"],
                            "errors": parsed["errors"], "skipped": parsed["skipped"],
                            "report_files": [str(f.relative_to(ws)) for f in files],
                            "log": str(log), "output_tail": tail if status != "passed" else ""})
        elif s["type"] == "http":
            start = time.monotonic()
            code, _, tail = _run(s["setup"], ws, int(s.get("timeout_s", 1200)), log, env)
            checks = []
            try:
                if code == 0:
                    deadline = time.monotonic() + int(s.get("wait_s", 180))
                    # {backend}/{frontend}/{db} in URLs become this artifact's allocated ports
                    pending = [{**c, "url": c["url"].format(**ports)} for c in s["checks"]]
                    seen: dict[str, Any] = {}
                    while pending and time.monotonic() < deadline:
                        for c in list(pending):
                            got, err = _http(c["url"])
                            seen[c["name"]] = got if got is not None else err
                            if got == c["expect_status"]:
                                checks.append({**c, "status": got, "passed": True})
                                pending.remove(c)
                        if pending:
                            time.sleep(5)
                    for c in pending:
                        checks.append({**c, "status": seen.get(c["name"]), "passed": False})
            finally:
                _run(s["teardown"], ws, 300, log, env)
            passed = code == 0 and checks and all(c["passed"] for c in checks)
            n_fail = sum(1 for c in checks if not c["passed"])
            totals["tests"] += len(checks)
            totals["failures"] += n_fail
            case_names += [f"smoke.{c['name']}" for c in checks]
            failed_cases += [{"suite": s["name"], "name": f"smoke.{c['name']}", "kind": "failure",
                              "message": f"expected {c['expect_status']} from {c['url']}, got {c['status']}"}
                             for c in checks if not c["passed"]]
            if code != 0:
                totals["errors"] += 1
                failed_cases.append({"suite": s["name"], "name": "smoke.setup", "kind": "error",
                                     "message": f"setup exited {code}"})
            results.append({"name": s["name"], "type": "http", "status": "passed" if passed else "failed",
                            "exit_code": code, "duration_ms": int((time.monotonic() - start) * 1000),
                            "tests": len(checks), "failures": n_fail, "checks": checks, "log": str(log),
                            "output_tail": "" if passed else tail})
        elif s["type"] == "command":
            # exit code plus optional expected output files (e.g. a production build)
            code, ms, tail = _run(s["command"], ws, int(s.get("timeout_s", 900)), log, env)
            missing = [g for g in s.get("expect_files", []) if not list(ws.glob(g))]
            passed = code == 0 and not missing
            totals["tests"] += 1
            totals["failures"] += 0 if passed else 1
            case_names.append(f"{s['name']}.command")
            if not passed:
                failed_cases.append({"suite": s["name"], "name": f"{s['name']}.command", "kind": "failure",
                                     "message": f"exit {code}" + (f"; missing {missing}" if missing else "")})
            results.append({"name": s["name"], "type": "command", "status": "passed" if passed else "failed",
                            "exit_code": code, "duration_ms": ms, "tests": 1, "failures": 0 if passed else 1,
                            "missing_files": missing, "log": str(log), "output_tail": "" if passed else tail})
        else:
            raise LatticeError("E_PROCEDURE", f"unknown suite type {s['type']}")
        rt.progress(ctx, f"suite {s['name']} {results[-1]['status']}")
    return {"passed": bool(results) and all(r["status"] == "passed" for r in results), "totals": totals,
            "suites": results, "case_names": case_names, "failed_cases": failed_cases,
            "docker": why}


# ── native control / delivery commands ──────────────────────────────────
def _zip_dir(src: Path, dest: Path) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for p in src.rglob("*"):
            rel = p.relative_to(src)
            if any(part in SKIP_DIRS for part in rel.parts) or not p.is_file():
                continue
            z.write(p, rel.as_posix())
            n += 1
    return n


def status(rt: "Runtime", ctx: "ExecContext") -> dict:
    if ctx.artifact_id:
        m = rt.store.manifest(ctx.artifact_id)
        return {"artifact": {k: m.get(k) for k in ("id", "title", "created_at", "updated_at", "workspace")},
                "profile": (m.get("profile") or {}).get("name"), "stack": (m.get("stack") or {}).get("name"),
                "stages": m["stages"], "history": m["history"][-20:],
                "running": [r for r in rt.store.running() if r.get("artifact_id") == ctx.artifact_id]}
    return {"artifacts": [{"id": a, "stages": {k: v["status"] for k, v in rt.store.manifest(a)["stages"].items()}}
                          for a in rt.store.list_ids()],
            "running": rt.store.running()}


def checkpoint(rt: "Runtime", ctx: "ExecContext") -> dict:
    label = ctx.params.get("label") or now_iso().replace(":", "").replace("-", "")[:15]
    adir = rt.store.artifact_dir(ctx.artifact_id)
    cdir = adir / "checkpoints" / label
    if cdir.exists():
        raise LatticeError("E_PARAM", f"checkpoint '{label}' already exists")
    cdir.mkdir(parents=True)
    shutil.copy2(adir / "manifest.json", cdir / "manifest.json")
    if (adir / "stages").exists():
        shutil.copytree(adir / "stages", cdir / "stages")
    ws = ctx.workspace
    files = _zip_dir(ws, cdir / "workspace.zip") if ws and ws.exists() else 0
    return {"label": label, "path": str(cdir), "workspace_files": files}


def rollback(rt: "Runtime", ctx: "ExecContext") -> dict:
    label = ctx.params.get("to")
    if not label:
        raise LatticeError("E_PARAM", "rollback requires to=<checkpoint label>")
    adir = rt.store.artifact_dir(ctx.artifact_id)
    cdir = adir / "checkpoints" / label
    if not cdir.exists():
        raise LatticeError("E_PARAM", f"no checkpoint '{label}'")
    moved = None
    ws = ctx.workspace
    if ws and ws.exists():
        moved = rt.store.root / "archive" / f"{ctx.artifact_id}-workspace-before-rollback-{int(time.time())}"
        moved.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(ws), moved)  # non-destructive: previous workspace kept in archive
    if (cdir / "workspace.zip").exists() and ws:
        ws.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(cdir / "workspace.zip") as z:
            z.extractall(ws)
    manifest = read_json(cdir / "manifest.json")
    manifest.setdefault("history", []).append({"stage": "rollback", "to": label, "at": now_iso()})
    write_json(adir / "manifest.json", manifest)
    return {"restored": label, "previous_workspace_archived_to": str(moved) if moved else None}


def approve(rt: "Runtime", ctx: "ExecContext") -> dict:
    cmd = ctx.params.get("command")
    if not cmd or cmd not in rt.registry.commands:
        raise LatticeError("E_PARAM", "approve requires command=<name of a registered command>")
    if not rt.interactive or not sys.stdin.isatty():
        raise LatticeError("E_APPROVAL_REQUIRED",
                           "approvals must be confirmed by a person at an interactive terminal: "
                           f"run `lattice approve {ctx.artifact_id} {cmd}`")
    answer = input(f"Approve '{cmd}' for {ctx.artifact_id}? Type the artifact id to confirm: ").strip()
    if answer != ctx.artifact_id:
        raise LatticeError("E_APPROVAL_REQUIRED", "approval not confirmed")
    entry = {"artifact_id": ctx.artifact_id, "command": cmd, "note": ctx.params.get("note"), "approver": "interactive"}
    rt.store.add_approval(entry)
    return {"approved": entry}


def package(rt: "Runtime", ctx: "ExecContext") -> dict:
    dest = rt.store.root / "packages" / f"{ctx.artifact_id}-{int(time.time())}.zip"
    n = _zip_dir(ctx.workspace, dest)
    return {"package": str(dest), "files": n, "bytes": dest.stat().st_size}


def deploy(rt: "Runtime", ctx: "ExecContext") -> dict:
    raise LatticeError("E_UNAVAILABLE", "no deployment integration is configured in Lattice v0.1; "
                                        "the approval was recorded but nothing was deployed")


def report(rt: "Runtime", ctx: "ExecContext") -> dict:
    m = rt.store.manifest(ctx.artifact_id)
    lines = [f"# {m['id']}: {m['title']}", "", f"Created {m['created_at']}; workspace `{m.get('workspace')}`", ""]
    for stage, st in m["stages"].items():
        out = rt.store.stage_output(ctx.artifact_id, stage)
        rec = read_json(rt.store.root / st["file"])
        lines += [f"## {stage}: {st['status']}", "", f"run `{st['run_id']}`; validation passed: {st['validation_passed']}", ""]
        for f in rec["validation"].get("findings", []):
            lines.append(f"- **{f['severity']}** `{f['rule']}`: {f['message']}")
        summary = (out or {}).get("summary") or (out or {}).get("overview")
        if summary:
            lines += ["", summary]
        lines.append("")
    path = rt.store.artifact_dir(ctx.artifact_id) / "report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return {"report": str(path)}


def revalidate(rt: "Runtime", ctx: "ExecContext") -> dict:
    m = rt.store.manifest(ctx.artifact_id)
    stages = [ctx.params["stage"]] if ctx.params.get("stage") else list(m["stages"])
    out = {}
    for st in stages:
        if st not in m["stages"]:
            raise LatticeError("E_PARAM", f"artifact has no stage '{st}'")
        rec = read_json(rt.store.root / m["stages"][st]["file"])
        out[st] = rt.validate_output(st, rec["output"], ctx, rec.get("validation", {}).get("params", {}))
    return {"stages": out, "passed": all(v["passed"] for v in out.values())}


NATIVE = {"status": status, "checkpoint": checkpoint, "rollback": rollback, "approve": approve, "package": package,
          "deploy": deploy, "report": report, "revalidate": revalidate}
PROCEDURES = {"run_test_suites": run_test_suites}
