"""Reliability benchmark: run the same task N times as plain Claude Code ("baseline") and
through Lattice ("lattice"), score every run with the same deterministic rules, persist everything.

Suite file (YAML):
    name, version, description
    lattice:   {command, target, parameters}
    baseline:  {prompt}                    # direct `claude -p`, no schema / profile / validators
    evaluation:
      schema: requirement                  # JSON schema both modes are checked against
      coverage:  {LABEL: [keyword, ...]}   # an item is covered if ANY keyword appears in the requirement text
      constraints: {LABEL: [keyword, ...]} # must appear anywhere in the output
      success: {min_coverage: 0.9, require_schema: true, require_constraints: true}
"""
from __future__ import annotations

import itertools
import json
import re
import statistics
import tempfile
import time
from datetime import datetime
from pathlib import Path

import jsonschema
import yaml

from .adapters import AgentRequest, ToolPolicy, make_adapter
from .config import DEFAULT_CONFIG, deep_merge, load_config, load_registry
from .runtime import Runtime
from .store import write_json


def _extract_json(text: str):
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    cand = m.group(1) if m else text[text.find("{"): text.rfind("}") + 1] if "{" in text else ""
    try:
        return json.loads(cand)
    except (json.JSONDecodeError, TypeError):
        return None


def _requirement_text(out) -> str:
    if not isinstance(out, dict):
        return ""
    frs = out.get("functional_requirements") or []
    return json.dumps(frs, ensure_ascii=False).lower()


def score(out, ev: dict, registry) -> dict:
    schema = registry.schema(ev["schema"])
    schema_errors = [] if out is None else [e.message for e in jsonschema.Draft202012Validator(schema).iter_errors(out)]
    schema_ok = out is not None and not schema_errors
    fr_text = _requirement_text(out)
    all_text = json.dumps(out, ensure_ascii=False).lower() if out is not None else ""
    covered = sorted(k for k, kws in ev.get("coverage", {}).items() if any(w.lower() in fr_text for w in kws))
    cons = sorted(k for k, kws in ev.get("constraints", {}).items() if any(w.lower() in all_text for w in kws))
    cov = len(covered) / max(1, len(ev.get("coverage", {})))
    con = len(cons) / max(1, len(ev.get("constraints", {})))
    succ = ev.get("success", {})
    failure = None
    if out is None:
        failure = "no_parseable_output"
    elif succ.get("require_schema", True) and not schema_ok:
        failure = "schema"
    elif cov < succ.get("min_coverage", 0.9):
        failure = "coverage"
    elif succ.get("require_constraints", True) and con < 1.0:
        failure = "constraints"
    titles = sorted({re.sub(r"[^a-z ]", "", (f.get("title") or "").lower()).strip()
                     for f in (out or {}).get("functional_requirements", []) if isinstance(f, dict)})
    return {"schema_compliant": schema_ok, "schema_errors": schema_errors[:5], "coverage": round(cov, 3),
            "covered": covered, "missing": sorted(set(ev.get("coverage", {})) - set(covered)),
            "constraint_adherence": round(con, 3), "constraints_met": cons, "success": failure is None,
            "failure_category": failure,
            "fr_count": len((out or {}).get("functional_requirements", []) or []) if isinstance(out, dict) else 0,
            "fr_titles": titles}


def _jaccard(a: set, b: set) -> float:
    return 1.0 if not a and not b else len(a & b) / len(a | b)


def summarize(runs: list[dict]) -> dict:
    if not runs:
        return {}
    def mean(key):
        vals = [r[key] for r in runs if r.get(key) is not None]
        return round(statistics.mean(vals), 4) if vals else None
    pairs = list(itertools.combinations(runs, 2))
    cons = round(statistics.mean(_jaccard(set(a["score"]["covered"]), set(b["score"]["covered"]))
                                 for a, b in pairs), 3) if pairs else None
    fails: dict[str, int] = {}
    for r in runs:
        c = r["score"]["failure_category"] or r.get("error_code")
        if c:
            fails[c] = fails.get(c, 0) + 1
    frc = [r["score"]["fr_count"] for r in runs]
    return {
        "runs": len(runs),
        "schema_compliance_rate": round(sum(r["score"]["schema_compliant"] for r in runs) / len(runs), 3),
        "mean_requirement_coverage": round(statistics.mean(r["score"]["coverage"] for r in runs), 3),
        "mean_constraint_adherence": round(statistics.mean(r["score"]["constraint_adherence"] for r in runs), 3),
        "task_success_rate": round(sum(r["score"]["success"] for r in runs) / len(runs), 3),
        "consistency_covered_items_jaccard": cons,
        "fr_count_mean": round(statistics.mean(frc), 2), "fr_count_stdev": round(statistics.pstdev(frc), 2),
        "mean_duration_ms": mean("duration_ms"), "mean_cost_usd": mean("cost_usd"),
        "mean_output_tokens": mean("output_tokens"),
        "failure_categories": fails,
    }


def run_bench(project_dir: Path, suite_path: Path, runs: int = 3, modes=("baseline", "lattice")) -> dict:
    suite = yaml.safe_load(suite_path.read_text(encoding="utf-8"))
    registry = load_registry()
    cfg = load_config(project_dir)
    adapter = make_adapter(cfg["agent"]["adapter"])
    ev = suite["evaluation"]
    results = {m: [] for m in modes}
    for i in range(runs):
        for mode in modes:
            started = time.monotonic()
            rec = {"mode": mode, "index": i}
            if mode == "baseline":
                with tempfile.TemporaryDirectory() as td:
                    resp = adapter.invoke(AgentRequest(
                        prompt=suite["baseline"]["prompt"], system="", output_schema=None,
                        policy=ToolPolicy("none", []), cwd=Path(td), model=cfg["agent"].get("model"),
                        timeout_s=int(cfg["agent"]["timeout_s"])))
                out = _extract_json(resp.text) if resp.ok else None
                rec.update(ok=resp.ok, error_code=resp.error_code, duration_ms=resp.duration_ms,
                           cost_usd=resp.cost_usd, output_tokens=(resp.token_usage or {}).get("output_tokens"),
                           model=resp.model, raw_text=resp.text[:200_000])
            else:
                with tempfile.TemporaryDirectory() as td:
                    rt = Runtime(Path(td), adapter=adapter, registry=registry,
                                 config=deep_merge(DEFAULT_CONFIG, {k: v for k, v in cfg.items()}))
                    spec = suite["lattice"]
                    res = rt.execute(rt.normalize(spec["command"], spec.get("target"), spec.get("parameters", {})))
                out = res["output"]
                ex = res["execution"]
                rec.update(ok=res["status"] == "completed", status=res["status"],
                           error_code=(res.get("error") or {}).get("code"), duration_ms=ex.get("duration_ms"),
                           cost_usd=ex.get("cost_usd"), output_tokens=(ex.get("token_usage") or {}).get("output_tokens"),
                           model=ex.get("model"), attempts=ex.get("attempts"),
                           lattice_validation=res["validation"])
            rec["wall_ms"] = int((time.monotonic() - started) * 1000)
            rec["output"] = out
            rec["score"] = score(out, ev, registry)
            results[mode].append(rec)
            print(f"[bench] {mode} run {i + 1}/{runs}: success={rec['score']['success']} "
                  f"coverage={rec['score']['coverage']} schema={rec['score']['schema_compliant']} "
                  f"cost={rec.get('cost_usd')}", flush=True)
    summary = {m: summarize(r) for m, r in results.items()}
    out_dir = project_dir / "bench" / "results"
    path = out_dir / f"{suite['name']}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    write_json(path, {"suite": suite, "suite_file": str(suite_path), "runs_per_mode": runs,
                      "registry_version": registry.version, "config_agent": cfg["agent"],
                      "summary": summary, "results": results})
    return {"summary": summary, "path": str(path)}
