import copy

from fixtures import DESIGN, REQUIREMENT, REVIEW, VERIFY, write_junit_cmd

from lattice.adapters import AgentResponse

SCRIPT = '''
requirement("Build a customer management application",
            stack=["Java", "React", "PostgreSQL"], standard="enterprise")
design("CRM-001")
build("CRM-001")
test("CRM-001")
review("CRM-001", criteria=["security", "architecture"])
verify("CRM-001", against="requirements")
'''


def run(rt, src=SCRIPT, **kw):
    from lattice.script import run_script
    return run_script(rt, src, **kw)


def test_end_to_end_core_pipeline(make_rt, tmp_path):
    rt, adapter = make_rt()
    out = run(rt)
    statuses = [(r["result"]["command"], r["result"]["status"]) for r in out["results"]]
    assert out["status"] == "completed", statuses
    assert [s for _, s in statuses] == ["completed"] * 6
    first = out["results"][0]["result"]
    assert first["artifact_id"] == "CRM-001"
    # Normalized result contract
    assert set(first) >= {"command", "status", "artifact_id", "output", "validation", "execution"}
    assert first["execution"]["model"] == "fixture" and first["execution"]["token_usage"]
    m = rt.store.manifest("CRM-001")
    assert set(m["stages"]) == {"requirement", "design", "build", "test", "review", "verify"}
    assert m["profile"]["name"] == "enterprise" and m["stack"]["name"] == "java_react_postgres"
    # test stage results come from the parsed JUnit file, not from the agent
    t = rt.store.stage_output("CRM-001", "test")
    assert t["totals"]["tests"] == 2 and "crm.CustomerIT.createsCustomer" in t["case_names"]
    v = rt.store.stage_output("CRM-001", "verify")
    assert v["verdict"]["result"] == "pass"
    # build ran in the workspace with the build tool policy; analysis commands had no tools
    by_cmd = {r.system.split("`")[1]: r for r in adapter.requests}
    assert by_cmd["build"].cwd == tmp_path / "apps" / "CRM-001"
    assert by_cmd["build"].policy.name == "build" and "Bash" in by_cmd["build"].policy.tools
    assert by_cmd["requirement"].policy.tools == []
    assert by_cmd["review"].policy.tools == ["Read", "Grep", "Glob"]
    # untrusted data is fenced in the prompt
    assert '<data name="target">Build a customer management application</data>' in by_cmd["requirement"].prompt
    # runs are recorded
    assert len(list((tmp_path / ".lattice" / "runs").iterdir())) == 6
    assert len((tmp_path / ".lattice" / "log.jsonl").read_text().splitlines()) == 6


def test_validation_failure_triggers_retry_with_feedback(make_rt):
    bad = copy.deepcopy(REQUIREMENT)
    bad["non_functional_requirements"] = bad["non_functional_requirements"][:2]  # drops profile controls
    rt, adapter = make_rt({"requirement": [bad, REQUIREMENT]})
    res = rt.run("requirement", "Build a CRM", stack=["Java", "React", "PostgreSQL"], standard="enterprise")
    assert res["status"] == "completed"
    assert res["execution"]["attempts"] == 2
    assert "failed automated validation" in adapter.requests[1].prompt
    assert "security.audit_logging" in adapter.requests[1].prompt


def test_validation_failure_is_reported_not_hidden(make_rt):
    bad = copy.deepcopy(REQUIREMENT)
    bad["constraints"] = []
    rt, _ = make_rt({"requirement": [bad, bad]})
    res = rt.run("requirement", "Build a CRM", stack=["Java", "React", "PostgreSQL"], standard="enterprise")
    assert res["status"] == "failed" and res["validation"]["passed"] is False
    assert any(f["rule"] == "stack_reflected" for f in res["validation"]["findings"])
    assert res["error"]["code"] == "E_VALIDATION"
    # the failed stage is still recorded for inspection
    assert rt.store.manifest(res["artifact_id"])["stages"]["requirement"]["status"] == "failed"


def test_schema_violation(make_rt):
    rt, _ = make_rt({"requirement": [{"title": "x"}, {"title": "x"}]})
    res = rt.run("requirement", "Build a CRM")
    assert res["status"] == "failed" and res["error"]["code"] == "E_SCHEMA"


def test_param_errors(make_rt):
    rt, _ = make_rt()
    r = rt.run("requirement", "x", colour="blue")
    assert r["error"]["code"] == "E_PARAM" and "colour" in r["error"]["message"]
    r = rt.run("requirement", "x", stack="Java")
    assert r["error"]["code"] == "E_PARAM"
    r = rt.run("requirement", "x", brief="../outside.md")
    assert r["error"]["code"] == "E_PARAM" and "outside" in r["error"]["message"]
    r = rt.run("requirement", "x", standard="platinum")
    assert r["error"]["code"] == "E_PROFILE"
    r = rt.run("verify", "CRM-001", against="vibes")
    assert r["error"]["code"] == "E_PARAM"


def test_unknown_artifact_and_missing_context(make_rt):
    rt, _ = make_rt()
    r = rt.run("design", "CRM-404")
    assert r["status"] == "failed" and r["error"]["code"] == "E_UNKNOWN_ARTIFACT"
    rt.run("requirement", "Build a CRM", stack=["Java", "React", "PostgreSQL"], standard="enterprise")
    r = rt.run("build", "CRM-001")
    assert r["status"] == "blocked" and r["error"]["code"] == "E_MISSING_CONTEXT"


def test_review_citing_nonexistent_file_fails(make_rt):
    review = copy.deepcopy(REVIEW)
    review["findings"][0]["file"] = "backend/src/Imaginary.java"
    rt, _ = make_rt({"review": [review, review]})
    out = run(rt, SCRIPT.replace('verify("CRM-001", against="requirements")', ""))
    res = out["results"][-1]["result"]
    assert res["command"] == "review" and res["status"] == "failed"
    assert any("does not exist" in f["message"] for f in res["validation"]["findings"])


def test_verify_rejects_fabricated_evidence(make_rt):
    v = copy.deepcopy(VERIFY)
    v["items"][0]["evidence"][0]["symbol"] = "CustomerController.deleteEverything"
    v["items"][0]["test_evidence"] = ["crm.ImaginaryTest.passes"]
    rt, _ = make_rt({"verify": [v, v]})
    out = run(rt)
    res = out["results"][-1]["result"]
    rules = {f["rule"] for f in res["validation"]["findings"]}
    assert res["status"] == "failed"
    assert {"evidence_symbols_exist", "test_evidence_matches_results"} <= rules


def test_verify_verdict_fails_when_must_requirement_unsatisfied(make_rt):
    v = copy.deepcopy(VERIFY)
    v["items"][1]["status"] = "partial"
    rt, _ = make_rt({"verify": [v, v]})
    res = run(rt)["results"][-1]["result"]
    assert res["status"] == "failed"
    assert res["output"]["verdict"]["result"] == "fail"
    assert "FR-02=partial" in res["output"]["verdict"]["reasons"][0]


def test_failing_tests_fail_the_test_command(make_rt, registry):
    failing = ('<testsuite><testcase classname="crm.A" name="b"><failure message="boom"/></testcase>'
               '</testsuite>')
    registry.stacks["java_react_postgres"]["test_suites"][0]["command"] = \
        write_junit_cmd("backend/target/surefire-reports/T.xml", failing)
    rt, _ = make_rt()
    out = run(rt)
    res = out["results"][3]["result"]
    assert res["command"] == "test" and res["status"] == "failed"
    assert res["output"]["failed_cases"][0]["message"] == "boom"
    assert len(out["results"]) == 4  # script halted


def test_missing_reports_is_an_error_not_a_pass(make_rt, registry):
    import sys
    registry.stacks["java_react_postgres"]["test_suites"][0]["command"] = [sys.executable, "-c", "pass"]
    rt, _ = make_rt()
    res = run(rt)["results"][3]["result"]
    assert res["status"] == "failed"
    assert res["output"]["suites"][0]["status"] == "error"


def test_build_validators_check_real_files(make_rt):
    rt, adapter = make_rt()
    out = run(rt, SCRIPT.split("test(")[0])
    assert out["status"] == "completed"
    # Remove a contract file and re-validate the stored build stage.
    (rt.project_dir / "apps" / "CRM-001" / "docker-compose.yml").unlink()
    res = rt.run("validate", "CRM-001", stage="build")
    assert res["output"]["passed"] is False


def test_agent_failure_surfaces_error(make_rt):
    fail = AgentResponse(ok=False, error_code="E_BUDGET", error="agent reported error_max_budget_usd")
    rt, _ = make_rt({"requirement": [fail]})
    res = rt.run("requirement", "x")
    assert res["status"] == "failed" and res["error"]["code"] == "E_BUDGET"


def test_deploy_requires_approval_then_reports_unavailable(make_rt):
    rt, _ = make_rt()
    run(rt)
    res = rt.run("deploy", "CRM-001")
    assert res["status"] == "awaiting_approval" and res["error"]["code"] == "E_APPROVAL_REQUIRED"
    # non-interactive approval is refused (agents and scripts cannot approve)
    res = rt.run("approve", "CRM-001", command="deploy")
    assert res["error"]["code"] == "E_APPROVAL_REQUIRED"
    rt.store.add_approval({"artifact_id": "CRM-001", "command": "deploy", "approver": "test"})
    res = rt.run("deploy", "CRM-001")
    assert res["status"] == "unavailable" and res["error"]["code"] == "E_UNAVAILABLE"
    # approvals are single-use
    res = rt.run("deploy", "CRM-001")
    assert res["status"] == "awaiting_approval"


def test_checkpoint_and_rollback(make_rt):
    rt, _ = make_rt()
    run(rt, SCRIPT.split("test(")[0])
    assert rt.run("checkpoint", "CRM-001", label="v1")["status"] == "completed"
    ws = rt.project_dir / "apps" / "CRM-001"
    (ws / "README.md").write_text("changed")
    rt.store.add_approval({"artifact_id": "CRM-001", "command": "rollback", "approver": "test"})
    res = rt.run("rollback", "CRM-001", to="v1")
    assert res["status"] == "completed", res
    assert (ws / "README.md").read_text() == "# CRM\n"
    assert res["output"]["previous_workspace_archived_to"]


def test_generic_command_and_decision_model(make_rt):
    decision = {"summary": "s", "options": [{"name": "A", "description": ""}, {"name": "B", "description": ""}],
                "criteria_scores": [{"option": o, "criterion": c, "score": 3, "rationale": "r"}
                                    for o in "AB" for c in ["benefit", "cost", "risk", "reversibility"]],
                "recommendation": {"option": "A", "rationale": "r", "gives_up": "g"}, "risks": [],
                "assumptions": ["x"]}
    rt, adapter = make_rt({"decide": decision})
    res = rt.run("decide", "Which queue?", options=["A", "B"])
    assert res["status"] == "completed", res
    assert "trade_off_analysis" in adapter.requests[-1].prompt
    incomplete = copy.deepcopy(decision)
    incomplete["criteria_scores"] = incomplete["criteria_scores"][:3]
    rt, _ = make_rt({"decide": [incomplete, incomplete]})
    res = rt.run("decide", "Which queue?", options=["A", "B"])
    assert res["status"] == "failed"
    assert rt.run("decide", "x", decision_model="astrology")["error"]["code"] == "E_DECISION_MODEL"


def test_status_and_report(make_rt):
    rt, _ = make_rt()
    run(rt)
    st = rt.run("status", "CRM-001")["output"]
    assert st["stages"]["verify"]["status"] == "completed"
    rep = rt.run("report", "CRM-001")["output"]["report"]
    assert "## verify: completed" in open(rep, encoding="utf-8").read()
