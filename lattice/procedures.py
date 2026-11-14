"""Built-in procedures (run by the runtime itself, no agent) and post-processing hooks.

Commands reference these by name from their .yaml:  mode: procedure / procedure: run_tests,
and  postprocess: [verify_verdict].
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING

from .errors import LatticeError
from .store import now_iso
from .validators import finding

if TYPE_CHECKING:
    from .runtime import ExecContext, Runtime


def _run(argv: list[str], cwd: Path, timeout: int, log: Path, env: dict | None = None) -> tuple[int | None, int]:
    start = time.monotonic()
    argv = list(argv)
    exe = shutil.which(argv[0])  # resolves npm -> npm.cmd on Windows
    if exe:
        argv[0] = exe
    with open(log, "a", encoding="utf-8", errors="replace") as lf:
        lf.write(f"\n$ {' '.join(argv)}   (cwd={cwd}, {now_iso()})\n")
        lf.flush()
        try:
            p = subprocess.run(argv, cwd=str(cwd), stdout=lf, stderr=subprocess.STDOUT, timeout=timeout,
                               stdin=subprocess.DEVNULL, env={**os.environ, **(env or {})})
            code = p.returncode
        except subprocess.TimeoutExpired:
            lf.write(f"\n[lattice] TIMEOUT after {timeout}s\n")
            code = None
        except FileNotFoundError as e:
            lf.write(f"\n[lattice] command not found: {e}\n")
            code = 127
    return code, int((time.monotonic() - start) * 1000)


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
                    failures += kind == "failure"
                    errors += kind == "error"
                    failed.append({"name": name, "kind": kind,
                                   "message": (el.get("message") or el.text or "").strip()[:1500]})
    return {"tests": tests, "failures": failures, "errors": errors, "skipped": skipped,
            "case_names": cases, "failed_cases": failed}


def run_tests(rt: "Runtime", ctx: "ExecContext") -> dict:
    """Run the caller's test commands in the workspace and parse the JUnit reports they write."""
    p = ctx.params
    ws = ctx.workspace
    if not ws or not ws.exists():
        raise LatticeError("E_MISSING_CONTEXT", f"workspace {ws} does not exist")
    if not p["run"]:
        raise LatticeError("E_PARAM", "test needs at least one command in run=[...]")
    log = ctx.run_dir / "test.log"
    # Remove stale reports so old results can never count as a pass.
    for g in p["reports"]:
        for old in ws.glob(g):
            old.resolve().relative_to(ws.resolve())
            if old.is_file():
                old.unlink()
    steps, ok = [], True
    for cmd in p["run"]:
        argv = shlex.split(cmd)
        if rt.sandbox:
            argv = rt.sandbox.wrap(argv, ws, ctx.env())
        rt.progress(ctx, f"test: {cmd}")
        code, ms = _run(argv, ws, int(p["timeout_s"]), log, None if rt.sandbox else ctx.env())
        steps.append({"command": cmd, "exit_code": code, "duration_ms": ms})
        if code != 0:
            ok = False
            break
    files = sorted({f for g in p["reports"] for f in ws.glob(g)})
    j = parse_junit(files)
    missing = [g for g in p["expect_files"] if not list(ws.glob(g))]
    suites = []
    if p["reports"]:
        st = "passed" if (j["tests"] and not j["failures"] and not j["errors"]) else ("error" if not j["tests"] else "failed")
        suites.append({"name": "junit", "type": "junit", "status": st, "tests": j["tests"],
                       "failures": j["failures"], "errors": j["errors"], "skipped": j["skipped"],
                       "report_files": [str(f.relative_to(ws)) for f in files]})
    suites.append({"name": "commands", "type": "command", "status": "passed" if ok else "failed",
                   "steps": steps})
    if p["expect_files"]:
        suites.append({"name": "expect_files", "type": "files", "status": "failed" if missing else "passed",
                       "missing": missing})
    tail = log.read_text(encoding="utf-8", errors="replace")[-3000:] if log.exists() else ""
    passed = all(s["status"] == "passed" for s in suites)
    return {"passed": passed,
            "totals": {k: j[k] for k in ("tests", "failures", "errors", "skipped")},
            "suites": suites, "case_names": j["case_names"], "failed_cases": j["failed_cases"],
            "log": str(log), "output_tail": "" if passed else tail,
            "sandbox": rt.sandbox.name if rt.sandbox else None}


PROCEDURES = {"run_tests": run_tests}


# ── post-processing hooks: (rt, ctx, output, findings) -> findings ───────
def tests_must_pass(rt, ctx, output, findings):
    if isinstance(output, dict) and not output.get("passed"):
        bad = [s["name"] for s in output.get("suites", []) if s["status"] != "passed"]
        findings.append(finding("tests_must_pass", f"not passing: {bad}; "
                                                   f"{len(output.get('failed_cases', []))} failing test cases"))
    return findings


def compute_verdict(spec: dict | None, verify_out: dict, test: dict | None) -> dict:
    """Deterministic verdict; the agent's per-item statuses are inputs, not the verdict itself."""
    status = {i["id"]: i["status"] for i in verify_out.get("items", [])}
    must = [r["id"] for r in (spec or {}).get("requirements", []) if r["priority"] == "must"]
    reasons = []
    unmet = [i for i in must if status.get(i) != "satisfied"]
    if unmet:
        reasons.append("must requirements not satisfied: " + ", ".join(f"{i}={status.get(i)}" for i in unmet))
    if test is None:
        reasons.append("no recorded test results")
    elif not test.get("passed"):
        reasons.append("recorded test run did not pass")
    counts: dict[str, int] = {}
    for s in status.values():
        counts[s] = counts.get(s, 0) + 1
    return {"result": "fail" if reasons else "pass", "reasons": reasons, "status_counts": counts,
            "must_requirements": len(must), "tests_passed": None if test is None else bool(test.get("passed"))}


def verify_verdict(rt, ctx, output, findings):
    if isinstance(output, dict) and not any(f["severity"] == "error" for f in findings):
        output["verdict"] = compute_verdict(ctx.spec, output, ctx.test)
        if output["verdict"]["result"] != "pass":
            findings.append(finding("verification_verdict", "; ".join(output["verdict"]["reasons"])))
    return findings


POSTPROCESS = {"tests_must_pass": tests_must_pass, "verify_verdict": verify_verdict}
