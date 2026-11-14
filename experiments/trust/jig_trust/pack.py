"""The Jig factory pack: how far can a Jig way of building software be trusted, and does writing the spec as
FACTS notes, or choosing the builder, change it?

  candidate  a way of working: the trial pipeline (trial.jig) with two choices, the spec format the builder reads
             ("prose" or "facts") and the builder ("opus" = Claude Opus through Claude Code, "luna" = GPT-6 Luna
             through Codex). Opus always writes the spec and does the checking, so only these two things vary.
             The control is OPUS_PROSE: the way the game factory works today.
  item       one hidden acceptance check of one game brief: "<BRIEF>-H<n>", six per brief. The six checks of a
             brief share one build (a cluster), so ranges resample briefs, not checks.
  run        the first item of a (candidate, brief) pair runs the whole Jig pipeline once in a fresh folder; the
             other five reuse that build. Then the brief's hidden tests (hidden/<BRIEF>.test.ts, written and frozen
             before any run, each proven on a reference implementation by check_references.py) are copied into
             the built app at src/__hidden__/ and run with vitest under the pack's own config.
  score      1 if the hidden check passes, 0 if it fails. A build that failed, has no src/logic.ts or does not
             compile scores 0 on all six (a design failure: the way of working did not deliver).
  firewall   the builder never sees a hidden test: they are copied in only after the pipeline has finished, and
             the pack voids a build whose agent event logs mention the hidden tests' folder or file names.

Lock 3 (at the user's request): take apart the script itself. Its parts are the spec format and three steps as
switches (the test step, the verify step, the fix rounds); each alternative is the step switched off, so the 16
combinations show what each step of the script contributes. Build out keeps the designer's two text parts.
Designer stages (added after the run started, lock 2): take apart splits the winner into its spec format and two
text parts (extra spec guidance, extra build guidance); the designer, Claude Opus with no tools, writes new versions
of the text parts from the engine's firewalled brief only, and the format's alternative is the other format.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from engine.pack import Pack, Paused

HERE = Path(__file__).resolve().parent
JIG_REPO = HERE.parents[2]                       # C:\dev\Lattice Script
COMPARE = ["TICTAC", "BOWL", "MINES", "G2048", "CONN4", "HANG"]
SEALED = ["LIFE", "MASTER", "SOKO", "BJACK", "LIGHTS", "YAHTZ"]
HARD = ["POKER", "REVERS", "CHECKR", "GOCAP", "CRIB", "CHESS"]   # pilot 2: harder comparison briefs
R1_SCREEN = ["SLIDE", "BATTLE", "HANOI"]           # added with the designer stages (lock 2): fresh briefs
R1_CONFIRM = ["SUDOKU", "PEGS", "WORDS"]
TEXT_SLOTS = ("spec_guidance", "build_guidance")
# The script's own steps, as switches (lock 3: take apart the script itself). Default = the script as it is.
SWITCHES = {"tests": ("on", "off"), "verify": ("on", "off"), "fixes": (2, 0)}
SLOT_MEANING = {
    "spec_guidance": "one extra instruction added to the constraints the spec writer (specify) must follow and "
                     "restate, for example how to describe the required functions or their edge cases",
    "build_guidance": "extra notes given to the builder with its first build (and kept in every fix round), for "
                      "example how to work, what to test first, or what to check before finishing",
}
MAX_TEXT = 500
CHECKS = [f"H{n}" for n in range(1, 7)]
CODES = {("prose", "opus"): "OP", ("facts", "opus"): "OF", ("prose", "luna"): "LP", ("facts", "luna"): "LF"}
FIREWALL_MARKERS = ("jig_trust", "__hidden__", "hidden-vitest")
HIDDEN_CONFIG = ("export default { test: { include: ['src/__hidden__/**/*.test.ts'], environment: 'node', "
                 "testTimeout: 20000 } };\n")


def candidate(fmt: str, builder: str, spec_guidance: str = "", build_guidance: str = "", tests: str = "on",
              verify: str = "on", fixes: int = 2) -> dict:
    """Equal contents give an equal id. Parts at their default (no guidance; tests, verify and 2 fix rounds on) are
    left out of the id, so the four founders keep the ids they had before later locks added parts."""
    body = {"format": fmt, "builder": builder, "pipeline": "trial.jig"}
    if spec_guidance:
        body["spec_guidance"] = spec_guidance
    if build_guidance:
        body["build_guidance"] = build_guidance
    for k, v in (("tests", tests), ("verify", verify), ("fixes", fixes)):
        if v != SWITCHES[k][0]:
            body[k] = v
    cid = "jf-" + hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:12]
    return {"id": cid, "spec_guidance": "", "build_guidance": "", "tests": "on", "verify": "on", "fixes": 2, **body}


class JigFactoryPack(Pack):
    name = "jig_factory"
    description = "Jig ways of working (spec format x builder) scored by hidden acceptance tests on game briefs"
    control = "OPUS_PROSE"

    def __init__(self, trials_dir="C:/dev/jig-trials", max_builds=4, max_cost_usd=45.0, offline=False,
                 jig_timeout_s=5400, hidden_timeout_s=300, designer="opus", compare_briefs=None):
        from .frozen import FROZEN
        changed = [f for f, h in FROZEN.items()
                   if not (HERE / f).exists()
                   or hashlib.sha256((HERE / f).read_bytes().replace(b"\r\n", b"\n")).hexdigest() != h]
        if changed:
            raise RuntimeError(f"frozen pack files changed since the freeze: {', '.join(changed)}")
        self.trials = Path(trials_dir)
        self.offline = offline
        self.designer = designer
        self.compare = list(compare_briefs or COMPARE)
        unknown = [b for b in self.compare if not (HERE / "briefs" / f"{b}.md").exists()]
        if unknown:
            raise ValueError(f"no brief for {unknown}")
        self.max_cost = float(max_cost_usd)
        self.jig_timeout = int(jig_timeout_s)
        self.hidden_timeout = int(hidden_timeout_s)
        self.sem = threading.Semaphore(int(max_builds))
        self.locks: dict[str, threading.Lock] = {}
        self.locks_guard = threading.Lock()
        self.cost_lock = threading.Lock()
        (self.trials / "requirements").mkdir(parents=True, exist_ok=True)
        (self.trials / "builds").mkdir(parents=True, exist_ok=True)

    # ── candidates and items ────────────────────────────────────────────
    def founders(self):
        return {"OPUS_PROSE": candidate("prose", "opus"), "OPUS_FACTS": candidate("facts", "opus"),
                "LUNA_PROSE": candidate("prose", "luna"), "LUNA_FACTS": candidate("facts", "luna")}

    def item_sets(self):
        return {"compare": [f"{b}-{h}" for b in self.compare for h in CHECKS],
                "r1_screen": [f"{b}-{h}" for b in R1_SCREEN for h in CHECKS],
                "r1_confirm": [f"{b}-{h}" for b in R1_CONFIRM for h in CHECKS],
                "sealed": [f"{b}-{h}" for b in SEALED for h in CHECKS]}

    def cluster_of(self, item):
        return item.split("-")[0]

    def failure_type(self, record):
        return record.get("failure_type")

    # ── one run ─────────────────────────────────────────────────────────
    def run(self, cand, item, ctx):
        brief, check = item.split("-")
        key = f"{cand['id']}-{brief}"
        with self.locks_guard:
            lock = self.locks.setdefault(key, threading.Lock())
        with lock:
            build = self._cached(key)
            if build is None or build.get("failure") == "infra":
                self._guard_cost()
                with self.sem:
                    build = self._build(cand, brief, key)
                (self.trials / "builds" / f"{key}.json").write_text(json.dumps(build, indent=1), encoding="utf-8")
        if build.get("failure") == "infra":
            return {"error": build.get("error"), "failure": "infra"}
        rec = {"build": key, "app_id": build.get("app_id"), "pipeline_status": build.get("pipeline_status"),
               "fixes": build.get("fixes"), "cost_usd": build.get("cost_usd"), "builder": cand["builder"],
               "format": cand["format"]}
        if build.get("failure") == "design":
            return {**rec, "error": build.get("error"), "failure": "design",
                    "failure_type": build.get("failure_type") or "build failed"}
        passed = (build.get("hidden") or {}).get(check)
        if passed is None:
            return {**rec, "error": f"hidden check {check} did not run", "failure": "design",
                    "failure_type": build.get("failure_type") or "hidden test did not run"}
        return {**rec, "score": 1.0 if passed else 0.0,
                "failure_type": None if passed else "hidden test failed"}

    def _variant(self, cand) -> int:
        """A game number unique to this designed candidate among those with the same format and builder (lock 3 fix:
        the earlier hash-based number let two candidates share a game id and each other's folder). Numbers are
        recorded in <trials>/variants.json, so a candidate keeps its number for every brief."""
        code = CODES[(cand["format"], cand["builder"])]
        path = self.trials / "variants.json"
        with self.locks_guard:
            reg = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            if cand["id"] not in reg:
                taken = {v for cid, v in reg.items() if not cid.startswith("_") and reg.get("_code_" + cid) == code}
                want = 100 + int(cand["id"][3:], 16) % 900
                while want in taken:
                    want = 100 + (want - 99) % 900
                reg[cand["id"]] = want
                reg["_code_" + cand["id"]] = code
                path.write_text(json.dumps(reg, indent=1), encoding="utf-8")
            return reg[cand["id"]]

    def _cached(self, key):
        p = self.trials / "builds" / f"{key}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def _guard_cost(self):
        spent = 0.0
        for p in (self.trials / "builds").glob("*.json"):
            try:
                spent += json.loads(p.read_text(encoding="utf-8")).get("cost_usd") or 0.0
            except (json.JSONDecodeError, OSError):
                pass
        if spent >= self.max_cost:
            raise Paused(f"reported Claude usage ${spent:.2f} reached max_cost_usd ${self.max_cost:.2f}")

    def _build(self, cand, brief, key) -> dict:
        # founders are <BRIEF><CODE>-001; a designed version gets its own number from its id
        designed = bool(cand.get("spec_guidance") or cand.get("build_guidance")) or any(
            cand.get(k, SWITCHES[k][0]) != SWITCHES[k][0] for k in SWITCHES)
        variant = self._variant(cand) if designed else 1
        app_id = f"{brief}{CODES[(cand['format'], cand['builder'])]}-{variant:03d}"
        out = {"key": key, "app_id": app_id, "started": time.time()}
        if self.offline:
            return self._offline(cand, brief, out)
        ws = self.trials / "apps" / app_id
        if ws.exists():
            shutil.rmtree(ws, ignore_errors=True)        # every build starts from an empty folder
        req = self.trials / "requirements" / f"{app_id}.md"
        shutil.copy2(HERE / "briefs" / f"{brief}.md", req)
        vars_path = self.trials / "builds" / f"{key}.vars.json"
        vars_path.write_text(json.dumps({"id": app_id, "brief": f"requirements/{app_id}.md",
                                         "format": cand["format"], "builder": cand["builder"],
                                         "spec_guidance": cand.get("spec_guidance") or "",
                                         "build_guidance": cand.get("build_guidance") or "",
                                         "tests": cand.get("tests", "on"), "verify_step": cand.get("verify", "on"),
                                         "max_fixes": int(cand.get("fixes", 2))}), encoding="utf-8")
        argv = [sys.executable, "-m", "jig", "--project", str(self.trials), "run", str(HERE / "trial.jig"),
                "--vars", str(vars_path), "--json", "--continue-on-error", "--replace"]
        try:
            p = subprocess.run(argv, cwd=str(JIG_REPO), capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=self.jig_timeout, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return {**out, "failure": "design", "failure_type": "pipeline timed out",
                    "error": f"the Jig pipeline ran past {self.jig_timeout}s"}
        (self.trials / "builds" / f"{key}.stderr.log").write_text(p.stderr or "", encoding="utf-8")
        try:
            res = json.loads(p.stdout)
        except json.JSONDecodeError:
            return {**out, "failure": "infra", "error": f"jig exited {p.returncode} without JSON: {p.stderr[-600:]}"}
        (self.trials / "builds" / f"{key}.result.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        steps = [r["result"] for r in res.get("results", [])]
        out["cost_usd"] = round(sum((s.get("execution") or {}).get("cost_usd") or 0.0 for s in steps), 4)
        out["fixes"] = sum(1 for s in steps if s.get("command") == "build") - 1
        out["pipeline_status"] = res.get("status")
        out["log"] = res.get("log")
        infra = [s for s in steps if (s.get("error") or {}).get("code") in ("E_AGENT_UNAVAILABLE", "E_UNAVAILABLE")
                 or re.search(r"rate.?limit|usage limit|quota|overloaded|503|529",
                              str((s.get("error") or {}).get("message") or ""), re.I)]
        if infra:
            e = infra[0].get("error") or {}
            return {**out, "failure": "infra", "error": f"{e.get('code')}: {str(e.get('message'))[:500]}"}
        if not ws.exists() or not (ws / "src" / "logic.ts").exists():
            return {**out, "failure": "design", "failure_type": "no src/logic.ts",
                    "error": f"the build did not produce src/logic.ts ({res.get('error') or res.get('status')})"}
        leak = self._firewall(steps)
        if leak:
            return {**out, "failure": "design", "failure_type": "firewall",
                    "error": f"an agent's events mention the hidden tests ({leak}); the build is void"}
        hidden = self._hidden(ws, brief, out)
        return {**out, **hidden}

    def _firewall(self, steps) -> str | None:
        """Any mention of the hidden tests' location in the agents' own event logs voids the build."""
        for s in steps:
            run_id = (s.get("execution") or {}).get("run_id")
            if not run_id:
                continue
            for f in (self.trials / ".jig" / "runs" / run_id).glob("agent-events-*.jsonl"):
                text = f.read_text(encoding="utf-8", errors="replace")
                for m in FIREWALL_MARKERS:
                    if m in text:
                        return f"{m} in {f.name} of run {run_id}"
        return None

    def _hidden(self, ws: Path, brief: str, out: dict) -> dict:
        d = ws / "src" / "__hidden__"
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HERE / "hidden" / f"{brief}.test.ts", d / f"{brief}.test.ts")
        (ws / "hidden-vitest.config.mjs").write_text(HIDDEN_CONFIG, encoding="utf-8")
        report = ws / "hidden-results" / "junit.xml"
        npx = shutil.which("npx") or "npx"
        try:
            p = subprocess.run([npx, "vitest", "run", "--config", "hidden-vitest.config.mjs", "--reporter=junit",
                                f"--outputFile={report}"], cwd=str(ws), capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=self.hidden_timeout)
            log = (p.stdout or "") + (p.stderr or "")
        except subprocess.TimeoutExpired:
            log = "hidden tests timed out"
        (ws / "hidden-results").mkdir(exist_ok=True)
        (ws / "hidden-results" / "output.log").write_text(log, encoding="utf-8")
        results = {h: False for h in CHECKS}
        if report.exists():
            try:
                for c in ET.parse(report).getroot().iter("testcase"):
                    m = re.search(r"> (H\d)\b", c.get("name") or "")
                    if m and m.group(1) in results:
                        results[m.group(1)] = c.find("failure") is None and c.find("error") is None \
                            and c.find("skipped") is None
            except ET.ParseError:
                pass
        n = sum(results.values())
        ftype = None if n == len(CHECKS) else ("logic does not compile or import" if n == 0 else "hidden test failed")
        return {"hidden": results, "hidden_passed": n, "failure_type": ftype}

    def _offline(self, cand, brief, out):
        """Seeded stand-in for tests of the pack and the engine wiring; its numbers mean nothing."""
        import random
        rnd = random.Random(f"{cand['id']}-{brief}")
        p = {"opus": 0.85, "luna": 0.65}[cand["builder"]] + (0.05 if cand["format"] == "facts" else 0.0)
        hidden = {h: rnd.random() < p for h in CHECKS}
        return {**out, "hidden": hidden, "hidden_passed": sum(hidden.values()), "cost_usd": 0.0, "fixes": 0,
                "pipeline_status": "completed", "failure_type": None}

    # ── parts: taking the winner apart, and building out (added in lock 2) ──
    def slots(self, kind):
        return ["format", *SWITCHES] if kind == "takeapart" else list(TEXT_SLOTS)

    def parts(self, cand, kind):
        return {"format": cand["format"], "spec_guidance": cand.get("spec_guidance") or "",
                "build_guidance": cand.get("build_guidance") or "", "tests": cand.get("tests", "on"),
                "verify": cand.get("verify", "on"), "fixes": cand.get("fixes", 2)}

    def compose(self, base, parts, changes, kind, extras):
        p = dict(parts)
        for k, v in changes.items():
            p[k] = v["value"] if isinstance(v, dict) else v
        return candidate(p["format"], base["builder"], p.get("spec_guidance") or "", p.get("build_guidance") or "",
                         p.get("tests", "on"), p.get("verify", "on"), int(p.get("fixes", 2)))

    def evidence(self, cand, records):
        """Aggregates only (counts and rates over this design's records): never a brief, a test or a per-item score."""
        recs = [r for r in records.values() if r]
        builds = {}
        for r in recs:
            builds.setdefault(r.get("build"), r)
        fails = {}
        for r in recs:
            if r.get("failure_type"):
                fails[r["failure_type"]] = fails.get(r["failure_type"], 0) + 1
        n = max(len(builds), 1)
        return {"builds": len(builds),
                "builds_needing_fix_rounds": sum(1 for b in builds.values() if (b.get("fixes") or 0) > 0),
                "mean_fix_rounds": round(sum((b.get("fixes") or 0) for b in builds.values()) / n, 2),
                "builds_that_failed_outright": sum(1 for b in builds.values() if b.get("failure") == "design"),
                "hidden_check_failures_by_type": fails}

    def write(self, kind, cand, parts, brief, slots, per_slot):
        """The designer (Claude Opus, no tools) writes new versions of the text parts from the engine's brief only.
        The format part has exactly one alternative: the other format."""
        out = {}
        for slot in slots:
            if slot == "format":
                other = "prose" if parts["format"] == "facts" else "facts"
                out[slot] = [{"value": other, "rationale": f"the other spec format ({other})"}]
                continue
            if slot in SWITCHES:          # a step of the script: its alternative is the step switched off
                on, off = SWITCHES[slot]
                alt = off if parts.get(slot, on) == on else on
                why = {"tests": "no test step: the builder's own tests are not run and do not feed the fix rounds",
                       "verify": "no verify step: no AI check of the requirements, so fix rounds see only the tests",
                       "fixes": "no fix rounds: one build, as it comes"}[slot]
                out[slot] = [{"value": alt, "rationale": why}]
                continue
            out[slot] = self._design(slot, parts.get(slot) or "", brief, per_slot)
        return out, {}

    def _design(self, slot, current, brief, per_slot):
        if self.offline:
            return [{"value": f"offline {slot} version {i + 1}", "rationale": "offline stand-in"}
                    for i in range(per_slot)]
        prompt = (
            "You are the designer in a Reality Engine run. The candidates are ways of building a small browser game "
            "with an AI builder from a short written brief, in a fixed pipeline: an AI writes a spec, the builder "
            "writes the code and its own tests, real tests run, an AI verifies every requirement, and up to two fix "
            "rounds follow. Each finished game is scored by acceptance tests of its game rules that nobody in the "
            "pipeline sees.\n\n"
            f"Write {per_slot} new version(s) of ONE part, '{slot}': {SLOT_MEANING[slot]}.\n"
            f"Its current value is: {json.dumps(current) if current else '(empty: nothing is added today)'}\n\n"
            f"Rules: each version is plain instructions in English, at most {MAX_TEXT} characters, general to any "
            "such game (you do not know which games are used), different from the current value and from each "
            "other, and it must not ask anyone to look for unseen tests. "
            'Return only JSON: {"alts": [{"value": "...", "rationale": "..."}]}\n\n'
            "What has been measured so far (the engine's brief):\n" + str(brief.get("text") or brief)[:12000])
        reasons: list[str] = []
        for _ in range(3):
            ask = prompt + ("\n\nYour last answer was rejected: " + "; ".join(reasons) if reasons else "")
            p = subprocess.run(["claude", "-p", "--model", self.designer, "--output-format", "text", "--tools", "",
                                "--no-session-persistence"], input=ask, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=600, cwd=str(self.trials))
            txt = p.stdout.strip()
            try:
                alts = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])["alts"]
            except (ValueError, KeyError, TypeError):
                reasons = ["the answer was not the JSON object asked for"]
                continue
            reasons, good = [], []
            for a in alts if isinstance(alts, list) else []:
                v = a.get("value") if isinstance(a, dict) else None
                if not isinstance(v, str) or not v.strip():
                    reasons.append("a version is empty")
                elif len(v) > MAX_TEXT:
                    reasons.append(f"a version is {len(v)} characters, over {MAX_TEXT}")
                elif v.strip() == current.strip() or v.strip() in [g["value"] for g in good]:
                    reasons.append("a version repeats the current value or another version")
                elif re.search(r"hidden|answer key|sealed|unseen test", v, re.I):
                    reasons.append("a version mentions the unseen tests")
                else:
                    good.append({"value": v.strip(), "rationale": str(a.get("rationale") or "")[:400]})
            if len(good) >= per_slot:
                return good[:per_slot]
            reasons.append(f"{len(good)} valid version(s), {per_slot} needed")
        raise RuntimeError(f"the designer did not give {per_slot} valid version(s) of {slot}: {'; '.join(reasons)}")

    def report_extras(self, stage, scores, items):
        builds = {}
        for p in (self.trials / "builds").glob("jf-*.json"):
            if p.name.endswith((".vars.json", ".result.json")):
                continue
            try:
                b = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            builds[b.get("key", p.stem)] = {k: b.get(k) for k in ("app_id", "pipeline_status", "fixes", "cost_usd",
                                                                   "hidden_passed", "failure", "failure_type")}
        return {"builds": builds}
