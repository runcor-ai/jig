"""Variable binding, dotted lookups, id binding, resume."""
from fixtures import junit_cmd

from lattice.script import run_script


def test_bound_variable_passes_artifact_and_dotted_data(make_rt):
    rt, adapter = make_rt()
    out = run_script(rt, '''
spec = specify("A pong game", constraints=["React + TypeScript"])
build(spec, notes=spec.output.summary)
research(spec.output.title, question=spec.id)
''')
    assert out["status"] == "completed", out
    assert out["results"][0]["result"]["artifact_id"] == "PONG-001"   # from the agent's artifact_code
    by = {r.system.split("`")[1]: r for r in adapter.requests}
    assert '<data name="notes">Browser pong</data>' in by["build"].prompt
    assert '<data name="target">Pong</data>' in by["research"].prompt
    assert "PONG-001" in by["research"].prompt


def test_missing_dotted_path_is_a_clear_error(make_rt):
    rt, _ = make_rt()
    out = run_script(rt, 'spec = specify("x")\nbuild(spec, notes=spec.output.nope)\n')
    err = out["results"][1]["result"]["error"]
    assert err["code"] == "E_PARAM" and "spec.output.nope" in err["message"] and "available" in err["message"]


def test_result_without_artifact_cannot_be_used_as_target(make_rt):
    rt, _ = make_rt()
    out = run_script(rt, 'r = research("passkeys")\nbuild(r)\n')
    assert "has no artifact" in out["results"][1]["result"]["error"]["message"]


def test_forward_declared_literal_id(make_rt):
    rt, _ = make_rt()
    out = run_script(rt, 'specify("x")\nbuild("TOY-001")\n')
    assert out["results"][0]["result"]["artifact_id"] == "TOY-001", out


def test_rerun_requires_replace_or_resume(make_rt):
    rt, adapter = make_rt()
    src = f'''spec = specify("x", id="PONG-001")
build(spec)
test(spec, run=['{junit_cmd()}'])
'''
    assert run_script(rt, src)["status"] == "completed"
    assert run_script(rt, src)["error"]["code"] == "E_ARTIFACT_EXISTS"
    n = len(adapter.requests)
    out = run_script(rt, src, resume=True)
    assert out["status"] == "completed" and all(r["result"].get("skipped") for r in out["results"])
    assert len(adapter.requests) == n                                     # nothing re-run
    assert out["results"][0]["result"]["output"]["title"] == "Pong"        # resumed output available
    out = run_script(rt, src.replace("build(spec)", 'build(spec, notes="changed")'), resume=True)
    assert out["results"][1]["result"].get("skipped") is None              # changed inputs re-run
    out = run_script(rt, src, replace=True)
    assert out["status"] == "completed" and list((rt.store.root / "archive").iterdir())


def test_external_variables_including_null(make_rt):
    rt, _ = make_rt()
    out = run_script(rt, "research(topic, question=question)", variables={"topic": "x", "question": None})
    assert out["status"] == "completed", out


def test_parse_error_executes_nothing_and_failure_halts(make_rt):
    rt, adapter = make_rt()
    assert run_script(rt, 'specify("x")\nimport os\n')["error"]["code"] == "E_PARSE" and not adapter.requests
    out = run_script(rt, 'build("NOPE-009")\nspecify("x")\n')
    assert out["status"] == "failed" and out["executed"] == 1 and not adapter.requests


# ── strict Ref lookups ──────────────────────────────────────────────────
def _err(out, i=1):
    return out["results"][i]["result"]["error"]


def test_nested_missing_key_names_the_full_path(make_rt):
    rt, adapter = make_rt()
    out = run_script(rt, 'spec = specify("x")\nbuild(spec, notes=spec.output.components.missing)\n')
    e = _err(out)
    assert e["code"] == "E_PARAM"
    assert "'spec.output.components.missing' not found" in e["message"]
    assert "'spec.output.components' has no 'missing'" in e["message"]
    assert len(adapter.requests) == 1                     # build never ran


def test_path_through_a_non_mapping_fails(make_rt):
    rt, _ = make_rt()
    out = run_script(rt, 'spec = specify("x")\nbuild(spec, notes=spec.output.title.length)\n')
    assert "'spec.output.title' has no 'length'" in _err(out)["message"]


def test_output_of_a_failed_step_is_an_error_not_none(make_rt):
    rt, _ = make_rt({"specify": [{"bad": 1}, {"bad": 1}]})    # schema failure -> output kept but failed
    out = run_script(rt, 'r = research("x")\nspec = specify("y")\nresearch(r.output.summary, question=None)\n')
    assert out["status"] == "failed"
    rt2, _ = make_rt({"research": [__import__("lattice.adapters", fromlist=["AgentResponse"]).AgentResponse(
        ok=False, error_code="E_AGENT_FAILED", error="boom")] * 2})
    out = run_script(rt2, 'r = research("x")\nresearch(r.output.summary)\n', continue_on_error=True)
    e = _err(out)
    assert e["code"] == "E_PARAM" and "'r' has no output" in e["message"] and "ended 'failed'" in e["message"]


def test_external_variable_missing_key(make_rt):
    rt, _ = make_rt()
    out = run_script(rt, "research(row.topic, question=row.qestion)",
                     variables={"row": {"topic": "x", "question": "y"}})
    e = out["results"][0]["result"]["error"]
    assert "'row.qestion' not found" in e["message"] and "available: ['question', 'topic']" in e["message"]


def test_present_null_value_is_a_real_value(make_rt):
    rt, _ = make_rt()
    out = run_script(rt, "research(row.topic, question=row.question)", variables={"row": {"topic": "x",
                                                                                          "question": None}})
    assert out["status"] == "completed", out
