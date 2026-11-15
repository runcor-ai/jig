"""A Jig script called as one step of another (command definitions with mode: script)."""
import textwrap

import pytest
from fixtures import Responder, junit_cmd

from jig.adapters import FixtureAdapter
from jig.config import DEFAULT_CONFIG
from jig.loader import BUILTIN_DIR, CommandDefError, load_commands
from jig.runtime import Runtime
from jig.script import run_script

INNER = """
spec = specify(f"Build the game in {file}", id=id)
build(spec)
t = test(spec, run=[TEST])
result = {"id": spec.id, "tests": t.status, "file": file}
if t.status != "completed":
    fail(f"{id}: tests did not pass")
"""

MAKE = """
purpose: Build one game from a requirements file.
version: "1.0.0"
mode: script
script: pipelines/make.jig
target: {type: text, required: true, as: file}
parameters:
  id: {type: string}
continue_on_error: true
artifact: none
output_schema:
  type: object
  required: [id, tests]
  properties: {id: {type: string}, tests: {type: string}}
"""


def project(tmp_path, inner=INNER, make=MAKE, extra=None):
    (tmp_path / "pipelines").mkdir(exist_ok=True)
    (tmp_path / "commands").mkdir(exist_ok=True)
    (tmp_path / "pipelines" / "make.jig").write_text(
        inner.replace("TEST", f"'{junit_cmd()}'"), encoding="utf-8")
    (tmp_path / "commands" / "make.yaml").write_text(textwrap.dedent(make), encoding="utf-8")
    for name, text in (extra or {}).items():
        (tmp_path / name).write_text(textwrap.dedent(text), encoding="utf-8")
    cmds = load_commands(tmp_path, dirs=[("builtin", BUILTIN_DIR), ("project", tmp_path / "commands")])
    adapter = FixtureAdapter(Responder())
    return Runtime(tmp_path, adapter=adapter, config=DEFAULT_CONFIG, commands=cmds), adapter


FACTORY = """
GAMES = [{"id": "PONG-001", "file": "pong.md"}, {"id": "SNAKE-001", "file": "snake.md"}]
done = []
for g in GAMES:
    r = make(g.file, id=g.id)
    done.append(r.output.id + ": " + r.output.tests)
print(done)
"""


def test_a_script_calls_another_script_and_gets_its_result(tmp_path):
    rt, adapter = project(tmp_path)
    out = run_script(rt, FACTORY)
    assert out["status"] == "completed", out
    steps = [r["result"] for r in out["results"]]
    assert [s["command"] for s in steps] == ["make", "make"]
    assert steps[0]["output"] == {"id": "PONG-001", "tests": "completed", "file": "pong.md"}
    assert out["log"] == ['["PONG-001: completed", "SNAKE-001: completed"]']
    # the inner steps ran for real, on their own artifacts
    assert rt.store.exists("PONG-001") and rt.store.exists("SNAKE-001")
    assert rt.store.manifest("PONG-001")["stages"]["test"]["status"] == "completed"
    assert len([r for r in adapter.requests if "`specify`" in r.system]) == 2
    # the outer step's record lists the inner steps
    import json
    rec = json.loads((rt.store.root / "runs" / steps[0]["execution"]["run_id"] / "script.json").read_text())
    assert [s["command"] for s in rec["steps"]] == ["specify", "build", "test"]
    assert steps[0]["execution"]["steps"] == 3


def test_a_failing_inner_script_fails_the_step_but_keeps_its_result(tmp_path):
    rt, _ = project(tmp_path, inner=INNER.replace("TEST", f"'{junit_cmd('fail')}'"))
    out = run_script(rt, 'r = make("pong.md", id="PONG-001")\n')
    res = out["results"][0]["result"]
    assert out["status"] == "failed" and res["status"] == "failed"
    assert res["output"]["tests"] == "failed"
    assert any(f["rule"] == "script_failed" and "PONG-001: tests did not pass" in f["message"]
               for f in res["validation"]["findings"])


def test_with_continue_on_error_the_outer_script_decides(tmp_path):
    rt, _ = project(tmp_path, inner=INNER.replace("TEST", f"'{junit_cmd('fail')}'"))
    out = run_script(rt, 'r = make("pong.md", id="PONG-001")\nif r.status != "completed":\n'
                         '    print("needs a look: " + r.output.tests)\n', continue_on_error=True)
    assert out["status"] == "completed" and out["log"] == ["needs a look: failed"]


def test_the_result_is_checked_against_the_output_schema(tmp_path):
    rt, _ = project(tmp_path, inner='result = {"id": id}\n')
    res = run_script(rt, 'make("pong.md", id="PONG-001")\n')["results"][0]["result"]
    assert res["status"] == "failed" and res["error"]["code"] == "E_SCHEMA"


def test_resume_replays_through_the_nested_call(tmp_path):
    rt, adapter = project(tmp_path)
    assert run_script(rt, FACTORY)["status"] == "completed"
    n = len(adapter.requests)
    out = run_script(rt, FACTORY, resume=True)
    assert out["status"] == "completed" and all(r["result"].get("skipped") for r in out["results"])
    assert len(adapter.requests) == n
    # without --resume or --replace the inner specify refuses to overwrite PONG-001
    res = run_script(rt, FACTORY, continue_on_error=True)["results"][0]["result"]
    assert res["status"] == "failed" and "already exists" in res["validation"]["findings"][0]["message"]
    out = run_script(rt, FACTORY, replace=True)
    assert out["status"] == "completed" and len(adapter.requests) > n


def test_a_script_that_calls_itself_stops_at_the_depth_limit(tmp_path):
    rt, _ = project(tmp_path, inner='make(file, id=id)\n')
    res = run_script(rt, 'make("x.md", id="X-001")\n')["results"][0]["result"]
    assert res["status"] == "failed"
    assert "nested more than 3 deep" in res["validation"]["findings"][0]["message"] or \
        "nested more than 3 deep" in str(res)


@pytest.mark.parametrize("inner,make,msg", [
    (INNER, MAKE.replace("pipelines/make.jig", "pipelines/missing.jig"), "does not exist"),
    ("build(spec)\n", MAKE, "undefined variable 'spec'"),
    ("nosuch(file)\n", MAKE, "nosuch"),
    (INNER, MAKE.replace("script: pipelines/make.jig\n", ""), "needs `script: <file>.jig`"),
    (INNER, MAKE.replace("as: file", "as: id"), "clashes with a parameter"),
])
def test_bad_script_commands_are_reported_at_load(tmp_path, inner, make, msg):
    with pytest.raises(CommandDefError, match=msg.replace("`", ".").replace("(", ".").replace(")", ".")):
        project(tmp_path, inner=inner, make=make)


def test_continue_on_error_is_only_for_script_commands(tmp_path):
    bad = "purpose: x\nmode: procedure\nprocedure: run_tests\ncontinue_on_error: true\n"
    with pytest.raises(CommandDefError, match="continue_on_error applies only"):
        project(tmp_path, extra={"commands/bad.yaml": bad})


def test_the_repo_factory_is_a_few_lines_over_make_game(commands):
    from conftest import ROOT
    from jig.parser import Statement, parse, walk
    assert commands["make_game"]["mode"] == "script"
    stmts = parse((ROOT / "factory" / "factory.jig").read_text(encoding="utf-8"), set(commands))
    assert [s.command for s in walk(stmts) if isinstance(s, Statement)] == ["make_game"]
