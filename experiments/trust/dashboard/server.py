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
        for p in sorted((trials / "builds").glob("jf-*.json")):
            if p.name.endswith((".vars.json", ".result.json")):
                continue
            b = read(p, {})
            spent += b.get("cost_usd") or 0.0
            cid, _, brief = b.get("key", p.stem).rpartition("-")
            c = cands.get(cid, {})
            builds.append({"brief": brief, "app_id": b.get("app_id"), "builder": c.get("builder"),
                           "format": c.get("format"), "state": "done", "hidden_passed": b.get("hidden_passed"),
                           "fixes": b.get("fixes"), "cost_usd": b.get("cost_usd"), "failure": b.get("failure"),
                           "failure_type": b.get("failure_type"),
                           "minutes": round((p.stat().st_mtime - b["started"]) / 60, 1) if b.get("started") else None})
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
                "builds": builds, "spent_usd": round(spent, 2),
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
