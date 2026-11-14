from lattice.script import run_script

SCRIPT = '''
requirement("Build a CRM", stack=["Java", "React", "PostgreSQL"], standard="enterprise")
design("CRM-001")
'''


def test_forward_declared_id_binding(make_rt):
    rt, adapter = make_rt({"requirement": {**__import__("fixtures").REQUIREMENT, "artifact_code": "XYZ"}})
    out = run_script(rt, SCRIPT)
    assert out["status"] == "completed", out
    assert out["results"][0]["result"]["artifact_id"] == "CRM-001"  # script id wins over agent code


def test_rerun_requires_replace(make_rt):
    rt, _ = make_rt()
    assert run_script(rt, SCRIPT)["status"] == "completed"
    out = run_script(rt, SCRIPT)
    assert out["error"]["code"] == "E_ARTIFACT_EXISTS" and out["results"] == []
    out = run_script(rt, SCRIPT, replace=True)
    assert out["status"] == "completed"
    assert list((rt.store.root / "archive").iterdir())  # old artifact archived, not deleted


def test_variables(make_rt):
    rt, _ = make_rt()
    out = run_script(rt, 'crm = requirement("Build a CRM", stack=["Java","React","PostgreSQL"], '
                         'standard="enterprise")\ndesign(crm)\n')
    assert out["status"] == "completed"
    assert out["results"][1]["result"]["artifact_id"] == out["results"][0]["result"]["artifact_id"] == "CRM-001"


def test_agent_code_used_without_declaration(make_rt):
    rt, _ = make_rt()
    res = rt.run("requirement", "Build a CRM")
    assert res["artifact_id"] == "CRM-001"
    assert rt.run("requirement", "Build another CRM")["artifact_id"] == "CRM-002"


def test_parse_error_executes_nothing(make_rt):
    rt, adapter = make_rt()
    out = run_script(rt, 'requirement("x")\nimport os\n')
    assert out["error"]["code"] == "E_PARSE" and not adapter.requests


def test_halts_on_failure(make_rt):
    rt, adapter = make_rt()
    out = run_script(rt, 'design("CRM-009")\nrequirement("x")\n')
    assert out["status"] == "failed" and out["executed"] == 1 and not adapter.requests
