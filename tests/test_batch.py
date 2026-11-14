"""Parallel batches (real OS processes, canned agent), resume, and isolation primitives."""
import sys
import threading
from pathlib import Path

import yaml
from fixtures import junit_cmd

from jig.batch import format_summary, run_batch
from jig.store import Store

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FAKE = [sys.executable, str(HERE / "fake_jig.py")]


def write_pipeline(tmp_path: Path) -> Path:
    p = tmp_path / "app.jig"
    p.write_text(f'''spec = specify(goal, constraints=constraints, id=id)
build(spec)
test(spec, run=['{junit_cmd()}'])
verify(spec)
''')
    return p


def test_batch_runs_items_in_parallel_and_resumes(tmp_path):
    items = tmp_path / "apps.yaml"
    items.write_text(yaml.safe_dump([
        {"id": "AAA-001", "goal": "App A", "constraints": ["React + TypeScript"]},
        {"id": "BBB-001", "goal": "App B", "constraints": ["React + TypeScript"]},
        {"id": "bad id", "goal": "App C", "constraints": ["React + TypeScript"]},
    ]))
    script = write_pipeline(tmp_path)
    log = []
    s = run_batch(tmp_path, items, script, parallel=3, echo=log.append, jig_cmd=FAKE)
    by = {i["id"]: i for i in s["items"]}
    assert by["AAA-001"]["status"] == by["BBB-001"]["status"] == "completed", s
    assert by["bad id"]["status"] == "failed" and by["bad id"]["failed_at"] == "specify"
    st = Store(tmp_path / ".jig")
    assert set(st.manifest("AAA-001")["stages"]) == {"specify", "build", "test", "verify"}
    assert (tmp_path / "apps" / "BBB-001" / "README.md").exists()
    assert "2/3 completed" in format_summary(s)
    log.clear()
    s2 = run_batch(tmp_path, items, script, parallel=3, resume=True, echo=log.append, jig_cmd=FAKE)
    assert {i["id"] for i in s2["items"] if i.get("skipped")} == {"AAA-001", "BBB-001"}


def test_research_batch(tmp_path):
    s = run_batch(tmp_path, ROOT / "examples/batches/research.yaml", ROOT / "examples/pipelines/research.jig",
                  parallel=3, echo=lambda m: None, jig_cmd=FAKE)
    assert s["completed"] == s["total"] == 3, s


def test_parallel_id_claims_are_unique(tmp_path):
    store = Store(tmp_path / ".jig")
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
    rt, _ = make_rt()
    a = rt.run("specify", "A", id="AAA-001")["artifact_id"]
    b = rt.run("specify", "B", id="BBB-001")["artifact_id"]
    assert set(rt.store.manifest(a)["ports"].values()).isdisjoint(rt.store.manifest(b)["ports"].values())
