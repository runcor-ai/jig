"""Parallel batches, resume, external variables, research checks, isolation."""
import copy
import sys
import threading
from pathlib import Path

import yaml
from fixtures import RESEARCH, REQUIREMENT

from lattice.batch import format_summary, run_batch
from lattice.script import run_script
from lattice.store import Store

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FAKE = [sys.executable, str(HERE / "fake_lattice.py")]

SIMPLE_REQ = {**REQUIREMENT,
              "non_functional_requirements": [
                  {"id": "NFR-01", "category": "security", "description": "validate", "source": "profile:security.input_validation"},
                  {"id": "NFR-02", "category": "quality", "description": "tests", "source": "profile:quality.automated_tests"},
                  {"id": "NFR-03", "category": "quality", "description": "readme", "source": "profile:quality.documentation"}],
              "constraints": [{"id": "C-01", "description": "React with TypeScript", "source": "stack:react_vite"},
                              {"id": "C-02", "description": "Data in browser localStorage", "source": "stack:react_vite"}]}


# ── research ────────────────────────────────────────────────────────────
def test_research_sources_checked_against_session(make_rt):
    rt, adapter = make_rt()
    res = rt.run("research", "Passkey adoption", question="How widespread?")
    assert res["status"] == "completed", res["validation"]
    req = adapter.requests[0]
    assert req.policy.tools == ["WebSearch", "WebFetch"]          # web only, no files or shell
    assert "How widespread?" in req.prompt


def test_research_rejects_fabricated_url(make_rt):
    bad = copy.deepcopy(RESEARCH)
    bad["sources"][0]["url"] = "https://made-up.example/never-fetched"
    rt, _ = make_rt({"research": [bad, bad]})
    res = rt.run("research", "Passkey adoption")
    assert res["status"] == "failed"
    msgs = [f["message"] for f in res["validation"]["findings"] if f["rule"] == "research_sources_retrieved"]
    assert msgs and "made-up.example" in msgs[0]


def test_research_requires_sources_per_finding_and_minimum(make_rt):
    bad = copy.deepcopy(RESEARCH)
    bad["findings"][0]["source_ids"] = []
    rt, _ = make_rt({"research": [bad, bad]})
    res = rt.run("research", "Passkey adoption", min_sources=5)
    rules = {f["rule"] for f in res["validation"]["findings"]}
    assert {"research_findings_sourced", "research_min_sources"} <= rules


# ── variables and resume ────────────────────────────────────────────────
PIPELINE = (ROOT / "examples/pipelines/app.lat").read_text()


def test_pipeline_with_external_variables_simple_stack(make_rt):
    from fixtures import DESIGN
    simple_design = {**DESIGN, "repository_layout": [{"path": p, "purpose": "x"} for p in
                                                     ["package.json", "index.html", "src/", "README.md"]]}
    rt, adapter = make_rt({"requirement": SIMPLE_REQ, "design": simple_design})
    out = run_script(rt, PIPELINE, variables={"id": "TODO-001", "goal": "Todo app", "stack": ["React"],
                                              "standard": "simple"})
    assert [r["result"]["status"] for r in out["results"]][:2] == ["completed", "completed"], out
    m = rt.store.manifest("TODO-001")
    assert m["stack"]["name"] == "react_vite" and m["profile"]["name"] == "simple"
    build_req = next(r for r in adapter.requests if r.system.split("`")[1] == "build")
    assert "npm run build" in build_req.prompt and "docker compose run" not in build_req.prompt


def test_null_variable_is_allowed(make_rt):
    rt, _ = make_rt()
    out = run_script(rt, "research(topic, question=question)", variables={"topic": "x", "question": None})
    assert out["status"] == "completed", out


def test_resume_skips_completed_steps(make_rt):
    rt, adapter = make_rt()
    src = 'requirement("Build a CRM", stack=["Java","React","PostgreSQL"], standard="enterprise", id="CRM-001")\n' \
          'design("CRM-001")\n'
    assert run_script(rt, src)["status"] == "completed"
    n = len(adapter.requests)
    out = run_script(rt, src, resume=True)
    assert out["status"] == "completed"
    assert [r["result"].get("skipped") for r in out["results"]] == [True, True]
    assert len(adapter.requests) == n                        # no new agent calls
    out = run_script(rt, src.replace('design("CRM-001")', 'design("CRM-001", notes="changed")'), resume=True)
    assert out["results"][1]["result"].get("skipped") is None  # inputs changed -> re-run
    assert len(adapter.requests) == n + 1


# ── isolation for parallel work ─────────────────────────────────────────
def test_parallel_id_claims_are_unique(tmp_path):
    store = Store(tmp_path / ".lattice")
    ids, errors = [], []

    def claim():
        try:
            ids.append(store.create_artifact(None, "t", {}, code="APP")["id"])
        except Exception as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=claim) for _ in range(12)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors and len(set(ids)) == 12


def test_each_artifact_gets_its_own_ports(make_rt):
    rt, adapter = make_rt()
    a = rt.run("requirement", "A", id="AAA-001")["artifact_id"]
    b = rt.run("requirement", "B", id="BBB-001")["artifact_id"]
    pa, pb = rt.store.manifest(a)["ports"], rt.store.manifest(b)["ports"]
    assert set(pa.values()).isdisjoint(pb.values())


# ── real multi-process batch (canned agent) ─────────────────────────────
def test_batch_runs_items_in_parallel_and_resumes(tmp_path):
    items = tmp_path / "apps.yaml"
    items.write_text(yaml.safe_dump([
        {"id": "AAA-001", "goal": "App A", "stack": ["Java", "React", "PostgreSQL"], "standard": "enterprise"},
        {"id": "BBB-001", "goal": "App B", "stack": ["Java", "React", "PostgreSQL"], "standard": "enterprise"},
        {"id": "CCC-001", "goal": "App C", "stack": ["Java", "React", "PostgreSQL"], "standard": "nope"},
    ]))
    log = []
    s = run_batch(tmp_path, items, ROOT / "examples/pipelines/app.lat", parallel=3, echo=log.append,
                  lattice_cmd=FAKE)
    by = {i["id"]: i for i in s["items"]}
    assert by["AAA-001"]["status"] == by["BBB-001"]["status"] == "completed", s
    assert by["CCC-001"]["status"] == "failed" and by["CCC-001"]["failed_at"] == "requirement"
    assert "unknown profile" in by["CCC-001"]["error"]
    st = Store(tmp_path / ".lattice")
    assert set(st.manifest("AAA-001")["stages"]) == {"requirement", "design", "build", "test"}
    assert (tmp_path / "apps" / "BBB-001" / "README.md").exists()
    table = format_summary(s)
    assert "2/3 completed" in table and "failed at requirement" in table
    # resume: completed items are skipped entirely
    log.clear()
    s2 = run_batch(tmp_path, items, ROOT / "examples/pipelines/app.lat", parallel=3, resume=True,
                   echo=log.append, lattice_cmd=FAKE)
    assert {i["id"] for i in s2["items"] if i.get("skipped")} == {"AAA-001", "BBB-001"}
    assert any("skip" in m for m in log)


def test_research_batch(tmp_path):
    s = run_batch(tmp_path, ROOT / "examples/batches/research.yaml", ROOT / "examples/pipelines/research.lat",
                  parallel=3, echo=lambda m: None, lattice_cmd=FAKE)
    assert s["completed"] == s["total"] == 3, s
