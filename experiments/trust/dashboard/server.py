"""The Reality Engine dashboard for a run's work folder (read-only).

    py experiments/trust/dashboard/server.py <plan.json> [--port 8770]

GET /             index.html (read fresh on every request)
GET /status.json  one payload built from the work folder: the step, progress and events (state.json), live scores
                  per design from the records with cluster-bootstrap 95% ranges, the stage analyses, the trust
                  report, and, for the Jig factory pack, every build (trials/builds/*.json).
It never writes anything.
"""
from __future__ import annotations

import argparse
import json
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE_BOOT = 1000
# GPT-6 Luna API list prices, USD per million tokens (OpenAI developer docs, developers.openai.com/docs/models/gpt-6-luna,
# read 14 Nov 2026). Codex's input count includes cached tokens. Long-prompt (>272K) and cache-write rates are not
# applied. On a ChatGPT plan nothing is billed per token: this is what the same tokens would cost on the API.
LUNA_PRICE = {"input": 0.10, "cached": 0.01, "output": 0.50, "source": "developers.openai.com/docs/models/gpt-6-luna",
              "as_of": "2026-11-14"}


# Claude Opus 5.5 API list prices, USD per million tokens (Anthropic first-party rates via the claude-api reference,
# cached 2026-11-03): input $4, output $20, cache read $0.20, cache write 1.25x input (5-minute) or 2x (1-hour).
# Used only to estimate steps that were cut off before Claude Code reported their cost.
OPUS_PRICE = {"input": 4.0, "output": 20.0, "cache_read": 0.20, "cache_write_5m": 5.0, "cache_write_1h": 8.0}


def opus_usd(t: dict) -> float:
    return ((t.get("input") or 0) * OPUS_PRICE["input"] + (t.get("output") or 0) * OPUS_PRICE["output"]
            + (t.get("cache_read") or 0) * OPUS_PRICE["cache_read"]
            + (t.get("cache_write_5m") or 0) * OPUS_PRICE["cache_write_5m"]
            + (t.get("cache_write_1h") or 0) * OPUS_PRICE["cache_write_1h"]) / 1e6


def partial_claude_tokens(events_file: Path) -> dict:
    """Tokens of a Claude Code step that was cut off: sum the usage of each assistant message (once per message id)."""
    seen, t = set(), {"input": 0, "output": 0, "cache_read": 0, "cache_write_5m": 0, "cache_write_1h": 0}
    try:
        lines = events_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return t
    for ln in lines:
        try:
            e = json.loads(ln)
        except json.JSONDecodeError:
            continue
        m = e.get("message") if e.get("type") == "assistant" else None
        if not isinstance(m, dict) or not isinstance(m.get("usage"), dict) or m.get("id") in seen:
            continue
        seen.add(m.get("id"))
        u = m["usage"]
        cc = u.get("cache_creation") or {}
        t["input"] += u.get("input_tokens") or 0
        t["output"] += u.get("output_tokens") or 0
        t["cache_read"] += u.get("cache_read_input_tokens") or 0
        w1h = cc.get("ephemeral_1h_input_tokens") or 0
        t["cache_write_1h"] += w1h
        t["cache_write_5m"] += max((u.get("cache_creation_input_tokens") or 0) - w1h, 0)
    return t


PARTS = {"format": "facts", "tests": "on", "verify": "on", "fixes": 2}       # defaults of the script's parts


def part_value(c: dict, k: str):
    return c.get(k, PARTS[k])


def takeapart_live(work: Path, cands: dict, winner_id: str | None, n=LIVE_BOOT, seed=11):
    """Live effect of each part of the winner's script: per brief, the mean score of the versions with that part
    changed minus the versions without it; mean over briefs with a cluster-bootstrap 95% range over briefs."""
    folder = work / "records" / "takeapart"
    w = cands.get(winner_id or "")
    if not w or not folder.exists():
        return None
    by = {}                                     # cid -> {brief: [scores]}
    for cdir in folder.glob("*"):
        for rp in cdir.glob("*/record.json"):
            r = read(rp, {})
            if r.get("score") is None:
                continue
            by.setdefault(cdir.name, {}).setdefault(r.get("item", "").split("-")[0], []).append(float(r["score"]))
    changed = {cid: [k for k in PARTS if part_value(cands.get(cid, {}), k) != part_value(w, k)] for cid in by}
    designs = [{"id": cid, "changed": changed[cid], "n": sum(len(v) for v in by[cid].values()),
                "mean": (sum(sum(v) for v in by[cid].values()) / max(sum(len(v) for v in by[cid].values()), 1)),
                "fixes_used": None} for cid in by]
    briefs = sorted({b for v in by.values() for b in v})
    effects = {}
    for k in PARTS:
        diffs = {}
        for b in briefs:
            on = [s for cid in by if k in changed[cid] for s in by[cid].get(b, [])]
            off = [s for cid in by if k not in changed[cid] for s in by[cid].get(b, [])]
            if on and off:
                diffs[b] = sum(on) / len(on) - sum(off) / len(off)
        if not diffs:
            effects[k] = {"effect": None, "range": None, "briefs": 0}
            continue
        vals = list(diffs.values())
        mean = sum(vals) / len(vals)
        rng = None
        if len(vals) >= 2:
            rnd = random.Random(seed)
            sims = sorted(sum(rnd.choice(vals) for _ in vals) / len(vals) for _ in range(n))
            rng = [sims[int(0.025 * n)], sims[int(0.975 * n) - 1]]
        effects[k] = {"effect": mean, "range": rng, "briefs": len(vals)}
    return {"winner": {k: part_value(w, k) for k in PARTS}, "effects": effects, "designs": designs,
            "briefs": len(briefs)}


def luna_usd(t: dict) -> float:
    uncached = max((t.get("input") or 0) - (t.get("cached") or 0), 0)
    return (uncached * LUNA_PRICE["input"] + (t.get("cached") or 0) * LUNA_PRICE["cached"]
            + (t.get("output") or 0) * LUNA_PRICE["output"]) / 1e6


def read(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def boot_range(by_cluster: dict[str, list[float]], n=LIVE_BOOT, seed=7):
    """Mean and 95% cluster-bootstrap range over clusters (briefs), as the engine does."""
    clusters = [v for v in by_cluster.values() if v]
    if not clusters:
        return None, None
    flat = [x for v in clusters for x in v]
    mean = sum(flat) / len(flat)
    if len(clusters) < 2:
        return mean, None
    rnd = random.Random(seed)
    sims = []
    for _ in range(n):
        pick = [x for _ in clusters for x in rnd.choice(clusters)]
        sims.append(sum(pick) / len(pick))
    sims.sort()
    return mean, [sims[int(0.025 * n)], sims[int(0.975 * n) - 1]]


class Feed:
    def __init__(self, plan_path: Path):
        self.plan_path = plan_path
        self.lock = threading.Lock()
        self.cache, self.at = None, 0.0

    def get(self):
        with self.lock:
            if self.cache is None or time.time() - self.at > 2.0:
                self.cache, self.at = self.build(), time.time()
            return self.cache

    def build(self):
        plan = read(self.plan_path, {})
        work = Path(plan.get("work") or "")
        trials = Path((plan.get("pack_options") or {}).get("trials_dir") or "")
        st = read(work / "state.json", {}) or {}
        cands = {}
        for p in (work / "candidates").glob("*.json"):
            c = read(p, {})
            if c.get("id"):
                cands[c["id"]] = c
        # live scores: records/<folder>/<candidate id>/<item>/record.json
        live = {}
        for folder in sorted(p.name for p in (work / "records").glob("*") if p.is_dir()):
            designs = {}
            for cdir in (work / "records" / folder).glob("*"):
                by_cluster, label, n, failures = {}, None, 0, {}
                for rec_p in cdir.glob("*/record.json"):
                    r = read(rec_p, {})
                    label = label or r.get("design")
                    s = r.get("score")
                    if s is None:
                        continue
                    n += 1
                    by_cluster.setdefault(r.get("item", "").split("-")[0], []).append(float(s))
                    if r.get("failure_type"):
                        failures[r["failure_type"]] = failures.get(r["failure_type"], 0) + 1
                mean, rng = boot_range(by_cluster)
                c = cands.get(cdir.name, {})
                designs[label or cdir.name] = {"id": cdir.name, "n": n, "mean": mean, "range": rng,
                                               "builder": c.get("builder"), "format": c.get("format"),
                                               "failures": failures}
            live[folder] = designs
        builds = []
        spent = 0.0
        luna_tokens = {"input": 0, "output": 0, "cached": 0}
        claude_tokens = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
        for p in sorted((trials / "builds").glob("jf-*.json")):
            if p.name.endswith((".vars.json", ".result.json")):
                continue
            b = read(p, {})
            spent += b.get("cost_usd") or 0.0
            # Luna (Codex) reports tokens, not dollars: sum them from the pipeline's step records
            lt = {"input": 0, "output": 0, "cached": 0}
            ct = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
            res = read(p.with_name(p.stem + ".result.json"), {}) or {}
            for r in res.get("results", []):
                ex = (r.get("result") or {}).get("execution") or {}
                tu = ex.get("token_usage") or {}
                if ex.get("adapter") == "codex":
                    lt["input"] += tu.get("input_tokens") or 0
                    lt["output"] += tu.get("output_tokens") or 0
                    lt["cached"] += tu.get("cache_read_input_tokens") or 0
                elif ex.get("adapter") == "claude_code":
                    ct["input"] += tu.get("input_tokens") or 0
                    ct["output"] += tu.get("output_tokens") or 0
                    ct["cache_write"] += tu.get("cache_creation_input_tokens") or 0
                    ct["cache_read"] += tu.get("cache_read_input_tokens") or 0
            for k in lt:
                luna_tokens[k] += lt[k]
            for k in ct:
                claude_tokens[k] += ct[k]
            cid, _, brief = b.get("key", p.stem).rpartition("-")
            c = cands.get(cid, {})
            builds.append({"brief": brief, "app_id": b.get("app_id"), "builder": c.get("builder"),
                           "luna_tokens": lt["input"] + lt["output"], "luna_usd": round(luna_usd(lt), 4),
                           "claude_tokens": sum(ct.values()),
                           "format": c.get("format"), "state": "done", "hidden_passed": b.get("hidden_passed"),
                           "fixes": b.get("fixes"), "cost_usd": b.get("cost_usd"), "failure": b.get("failure"),
                           "failure_type": b.get("failure_type"),
                           "minutes": round((p.stat().st_mtime - b["started"]) / 60, 1) if b.get("started") else None})
        # Every step Jig ever ran for this pilot (its run records), so stopped or voided builds are counted too.
        active = {}              # game id -> when its current attempt started (its vars file was written)
        for v in (trials / "builds").glob("jf-*.vars.json"):
            if not v.with_name(v.name.replace(".vars.json", ".json")).exists():
                active[(read(v, {}) or {}).get("id")] = v.stat().st_mtime

        def run_started(rd: Path) -> float:
            try:
                return time.mktime(time.strptime(rd.name[:15], "%Y%m%d-%H%M%S"))
            except ValueError:
                return rd.stat().st_mtime

        def current(app, rd: Path) -> bool:
            """The step belongs to a game's attempt that is running now (not to an earlier, stopped attempt)."""
            return app in active and run_started(rd) >= active[app] - 5
        counted = set()          # run ids of steps that belong to a finished (scored) build
        for p in (trials / "builds").glob("jf-*.result.json"):
            for r in (read(p, {}) or {}).get("results", []):
                rid = ((r.get("result") or {}).get("execution") or {}).get("run_id")
                if rid:
                    counted.add(rid)
        stopped_done = {"claude_usd": 0.0, "luna": {"input": 0, "output": 0, "cached": 0}}
        steps = {"claude_usd": 0.0, "claude_tokens": {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0},
                 "luna_tokens": {"input": 0, "output": 0, "cached": 0}, "luna_steps": 0, "completed": 0,
                 "in_progress": 0, "cut_claude_tokens": {"input": 0, "output": 0, "cache_read": 0,
                                                          "cache_write_5m": 0, "cache_write_1h": 0},
                 "cut_claude_steps": 0, "cut_luna_steps": 0}
        for rd in (trials / ".jig" / "runs").glob("*"):
            inv = read(rd / "invocation.json", {}) or {}
            res = read(rd / "result.json")
            agent = ((inv.get("controls") or {}).get("agent")) or ""
            app = (inv.get("parameters") or {}).get("id") if inv.get("command") == "specify" else inv.get("target")
            if res:
                steps["completed"] += 1
                ex = res.get("execution") or {}
                tu = ex.get("token_usage") or {}
                if rd.name not in counted and not current(app, rd):   # finished step of a build that never finished
                    if ex.get("adapter") == "codex":
                        stopped_done["luna"]["input"] += tu.get("input_tokens") or 0
                        stopped_done["luna"]["output"] += tu.get("output_tokens") or 0
                        stopped_done["luna"]["cached"] += tu.get("cache_read_input_tokens") or 0
                    elif ex.get("adapter") == "claude_code":
                        stopped_done["claude_usd"] += ex.get("cost_usd") or 0.0
                if ex.get("adapter") == "codex":
                    steps["luna_steps"] += 1
                    steps["luna_tokens"]["input"] += tu.get("input_tokens") or 0
                    steps["luna_tokens"]["output"] += tu.get("output_tokens") or 0
                    steps["luna_tokens"]["cached"] += tu.get("cache_read_input_tokens") or 0
                elif ex.get("adapter") == "claude_code":
                    steps["claude_usd"] += ex.get("cost_usd") or 0.0
                    steps["claude_tokens"]["input"] += tu.get("input_tokens") or 0
                    steps["claude_tokens"]["output"] += tu.get("output_tokens") or 0
                    steps["claude_tokens"]["cache_write"] += tu.get("cache_creation_input_tokens") or 0
                    steps["claude_tokens"]["cache_read"] += tu.get("cache_read_input_tokens") or 0
                continue
            if current(app, rd) or inv.get("command") == "test":
                steps["in_progress"] += 1 if current(app, rd) else 0
                continue
            if agent == "luna":
                steps["cut_luna_steps"] += 1
            else:
                steps["cut_claude_steps"] += 1
                for f in rd.glob("agent-events-*.jsonl"):
                    for k, v in partial_claude_tokens(f).items():
                        steps["cut_claude_tokens"][k] += v
        avg_luna = luna_usd(steps["luna_tokens"]) / steps["luna_steps"] if steps["luna_steps"] else 0.0
        stopped = {
            "claude_reported_usd": round(stopped_done["claude_usd"], 2),
            "claude_cut_est_usd": round(opus_usd(steps["cut_claude_tokens"]), 2),
            "claude_cut_tokens": sum(steps["cut_claude_tokens"].values()),
            "luna_usd": round(luna_usd(stopped_done["luna"]) + steps["cut_luna_steps"] * avg_luna, 3),
            "cut_claude_steps": steps["cut_claude_steps"], "cut_luna_steps": steps["cut_luna_steps"],
        }
        done = {(x["app_id"]) for x in builds}
        for p in sorted((trials / "builds").glob("jf-*.vars.json")):
            v = read(p, {})
            if v.get("id") and v["id"] not in done:
                builds.append({"brief": v["id"].split("-")[0][:-2], "app_id": v["id"], "builder": v.get("builder"),
                               "format": v.get("format"), "state": "running",
                               "minutes": round((time.time() - p.stat().st_mtime) / 60, 1)})
        return {"plan": {k: plan.get(k) for k in ("name", "about", "control", "sets", "final", "run")},
                "now": time.strftime("%Y-%m-%d %H:%M:%S"),
                "state": {k: st.get(k) for k in ("step", "progress", "winner", "runner_up", "best", "opened",
                                                 "halted", "paused", "waiting_for")},
                "events": (st.get("events") or [])[-40:],
                "live": live, "analysis": read(work / "analysis.json", {}), "report": read(work / "report.json"),
                "builds": builds, "spent_usd": round(spent, 2), "luna_tokens": luna_tokens, "claude_tokens": claude_tokens, "stopped": stopped,
                "takeapart": takeapart_live(work, cands, st.get("winner_id")),
                "all_steps": {"claude_usd": round(steps["claude_usd"], 2), "claude_tokens": steps["claude_tokens"],
                              "luna_tokens": steps["luna_tokens"], "luna_usd": round(luna_usd(steps["luna_tokens"]), 3),
                              "completed": steps["completed"]},
                "luna_usd": round(luna_usd(luna_tokens), 2), "luna_price": LUNA_PRICE,
                "cost_cap_usd": (plan.get("pack_options") or {}).get("max_cost_usd")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--port", type=int, default=8770)
    a = ap.parse_args()
    feed = Feed(Path(a.plan).resolve())

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path.startswith("/status.json"):
                body, ctype = json.dumps(feed.get(), default=str).encode(), "application/json"
            elif self.path in ("/", "/index.html") or self.path.startswith("/?"):
                body, ctype = (HERE / "index.html").read_bytes(), "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    print(f"The Reality Engine dashboard: http://127.0.0.1:{a.port}/  ({a.plan})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
