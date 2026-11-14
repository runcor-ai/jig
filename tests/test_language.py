"""Control flow, expressions, data types, limits, and resume across loops (fixture adapter, no model calls)."""
import copy

import pytest

from fixtures import RESEARCH
from jig.adapters import AgentResponse
from jig.parser import ParseError, parse
from jig.script import run_script


def _research(summary):
    r = copy.deepcopy(RESEARCH)
    r["summary"] = summary
    return r


FAIL = AgentResponse(ok=False, error_code="E_AGENT_FAILED", error="boom")


def _log(rt, src, **kw):
    out = run_script(rt, src, **kw)
    assert out["status"] == "completed", out.get("error") or out
    return out["log"]


# ── pure computation (no agent calls) ───────────────────────────────────
def test_arithmetic_strings_and_conditions(make_rt):
    rt, adapter = make_rt()
    log = _log(rt, '''
n = 2 + 3 * 4
s = "a" + "b"
xs = [1, 2] + [3]
print(n, s, xs, 7 // 2, 7 % 3, 1 / 4, -n)
print(f"n is {n} and xs has {len(xs)}")
print(n > 10 and s == "ab", not xs, 3 in xs, "b" in s, null is None, 1 < 2 < 3)
print("big" if n > 10 else "small", xs[0], xs[-1], xs[1:], "hello"[1:3])
''')
    assert log == ["14 ab [1, 2, 3] 3 1 0.25 -14", "n is 14 and xs has 3", "true false true true true true",
                   "big 1 3 [2, 3] el"]
    assert not adapter.requests


def test_if_elif_else_for_while_break_continue(make_rt):
    rt, _ = make_rt()
    log = _log(rt, '''
total = 0
for i in range(10):
    if i == 7:
        break
    elif i % 2 == 0:
        continue
    else:
        total += i
print(total)
k = 0
while k < 3:
    k += 1
print(k)
for i, x in enumerate(["a", "b"]):
    print(i, x)
for key in {"b": 1, "a": 2}:
    print(key)
''')
    assert log == ["9", "3", "0 a", "1 b", "b", "a"]


def test_list_map_queue_set(make_rt):
    rt, _ = make_rt()
    log = _log(rt, '''
xs = list()
xs.append(3)
xs.push(1)
xs.extend([2, 2])
xs.sort()
print(xs, xs.pop(), xs.index(2), len(xs))
m = map()
m.put("a", 1)
m["b"] = 2
m["a"] += 10
print(m, m.get("z", 0), m.has("b"), "a" in m, m.keys(), m.items())
m.remove("b")
q = queue(["first"])
q.push("second")
print(q.peek(), q.pop(), len(q), q)
seen = set()
for x in ["a", "b", "a"]:
    seen.add(x)
print(seen, len(seen), seen.has("a"), seen.union(["c"]))
stack = []
stack.append("x")
stack.append("y")
print(stack.pop(), ", ".join(["p", "q"]), "A,B".split(","), " t ".strip().upper())
print(sorted([3, 1, 2]), min([4, 2]), max(1, 9), sum([1, 2, 3]), str(1.5), int("7") + 1)
''')
    assert log == ['[1, 2, 2] 3 1 3',
                   '{"a": 11, "b": 2} 0 true true ["a", "b"] [["a", 11], ["b", 2]]',
                   'first first 1 ["second"]',
                   '["a", "b"] 2 true ["a", "b", "c"]',
                   'y p, q ["A", "B"] T',
                   '[1, 2, 3] 2 9 6 1.5 8']


def test_data_structures_pass_to_commands_as_json(make_rt):
    rt, adapter = make_rt()
    out = run_script(rt, '''
q = queue(["passkeys"])
s = set(["b", "a"])
research(q.pop(), question=", ".join(sorted(list(s))))
''')
    assert out["status"] == "completed", out
    assert '<data name="target">passkeys</data>' in adapter.requests[0].prompt
    assert "a, b" in adapter.requests[0].prompt


# ── control flow around commands ────────────────────────────────────────
def test_retry_loop_on_step_output(make_rt):
    rt, adapter = make_rt({"research": [_research("not yet"), _research("not yet"), _research("done")]})
    log = _log(rt, '''
r = research("passkeys")
tries = 1
while r.output.summary != "done" and tries < 5:
    r = research("passkeys", question=f"attempt {tries}")
    tries += 1
print(tries, r.status, r.output.summary)
''')
    assert log == ["3 completed done"] and len(adapter.requests) == 3


def test_for_over_items_creates_one_artifact_each_and_collects_results(make_rt):
    rt, _ = make_rt()
    out = run_script(rt, '''
built = map()
for goal in ["pong", "tetris"]:
    spec = specify(goal)
    b = build(spec)
    built[spec.id] = b.status
print(built)
''')
    assert out["status"] == "completed", out
    assert out["log"] == ['{"PONG-001": "completed", "PONG-002": "completed"}']
    assert out["executed"] == 4 and out["total"] == 2


def test_bound_results_in_a_list_pass_as_artifact_ids(make_rt):
    rt, adapter = make_rt()
    out = run_script(rt, '''
specs = []
for g in ["a", "b"]:
    s = specify(g)
    specs.append(s)
for s in specs:
    if s:
        build(s)
''')
    assert out["status"] == "completed", out
    assert [r["result"]["artifact_id"] for r in out["results"][2:]] == ["PONG-001", "PONG-002"]


def test_failed_step_can_be_handled_with_continue_on_error(make_rt):
    rt, _ = make_rt({"research": [FAIL, FAIL]})
    out = run_script(rt, '''
r = research("x")
if r.status == "failed":
    print("fallback")
''', continue_on_error=True)
    assert out["log"] == ["fallback"]


def test_nested_explicit_ids_need_replace_and_replace_archives_in_the_loop(make_rt):
    rt, _ = make_rt()
    src = '''
for row in rows:
    s = specify(row.goal, id=row.id)
    build(s)
'''
    rows = {"rows": [{"id": "AAA-001", "goal": "a"}, {"id": "BBB-001", "goal": "b"}]}
    assert run_script(rt, src, variables=copy.deepcopy(rows))["status"] == "completed"
    again = run_script(rt, src, variables=copy.deepcopy(rows))
    assert again["status"] == "failed" and again["results"][0]["result"]["error"]["code"] == "E_ARTIFACT_EXISTS"
    rep = run_script(rt, src, variables=copy.deepcopy(rows), replace=True)
    assert rep["status"] == "completed", rep
    assert len(list((rt.store.root / "archive").iterdir())) == 2


# ── errors and limits ───────────────────────────────────────────────────
@pytest.mark.parametrize("src,msg", [
    ('x = "a" + 1', "cannot add string and int"),
    ('xs = [1]\nprint(xs[5])', "out of range"),
    ('m = {"a": 1}\nprint(m["b"])', "map has no key 'b'"),
    ('q = queue()\nq.pop()', "empty queue"),
    ('x = 1 / 0', "division by zero"),
    ('xs = [1]\nxs.upper()', "list has no method 'upper'"),
    ('for c in 5:\n  pass', "cannot loop over a int"),
    ('s = set()\ns.add([1])', "set item must be"),
    ('x, y = [1, 2, 3]', "cannot unpack"),
])
def test_script_errors_are_positioned(make_rt, src, msg):
    rt, _ = make_rt()
    out = run_script(rt, src)
    assert out["status"] == "failed" and msg in out["error"]["message"], out
    assert out["error"]["message"].startswith("line ")


def test_while_cap_size_limit_and_step_limit(make_rt):
    rt, _ = make_rt()
    out = run_script(rt, "x = 0\nwhile true:\n  x += 1\n")
    assert out["error"]["code"] == "E_SCRIPT" and "max_while_iterations" in out["error"]["message"]
    out = run_script(rt, 'x = "a" * 1000000')
    assert "max_items" in out["error"]["message"]
    out = run_script(rt, "xs = [1]\nfor i in range(30):\n  xs.extend(xs)\n")
    assert "max_items" in out["error"]["message"]
    rt.config = {**rt.config, "script": {"max_steps": 50, "max_while_iterations": 1000}}
    out = run_script(rt, "x = 0\nwhile x < 500:\n  x += 1\n")
    assert "max_steps" in out["error"]["message"]


def test_parse_errors_execute_nothing(make_rt):
    rt, adapter = make_rt()
    out = run_script(rt, 'research("x")\nfor x in range(3):\n  import os\n')
    assert out["error"]["code"] == "E_PARSE" and not adapter.requests


def test_break_inside_if_inside_loop_parses():
    st = parse("for x in [1]:\n  if x:\n    break\n", {"research"})
    assert st[0].body[0].body[0].__class__.__name__ == "Break"
    with pytest.raises(ParseError):
        parse("if true:\n  break\n", {"research"})


# ── resume across loops ─────────────────────────────────────────────────
LOOP = '''
for t in ["a", "b", "a"]:
    research(t)
'''


def test_resume_replays_repeated_identical_steps_in_a_loop(make_rt):
    rt, adapter = make_rt()
    assert run_script(rt, LOOP)["status"] == "completed"
    assert len(adapter.requests) == 3
    out = run_script(rt, LOOP, resume=True)
    assert out["status"] == "completed" and all(r["result"].get("skipped") for r in out["results"])
    assert len(adapter.requests) == 3                          # nothing re-run


def test_resume_continues_from_the_failed_step(make_rt):
    rt, adapter = make_rt({"research": [_research("one"), FAIL, FAIL]})
    out = run_script(rt, LOOP)
    assert out["status"] == "failed" and out["executed"] == 2
    n = len(adapter.requests)                                  # 1 ok + 2 failed attempts
    out = run_script(rt, LOOP, resume=True)
    assert out["status"] == "completed", out
    assert [bool(r["result"].get("skipped")) for r in out["results"]] == [True, False, False]
    assert len(adapter.requests) == n + 2


def test_resume_stops_replaying_at_the_first_changed_step(make_rt):
    rt, adapter = make_rt()
    run_script(rt, LOOP)
    out = run_script(rt, LOOP.replace('"b"', '"c"'), resume=True)
    assert [bool(r["result"].get("skipped")) for r in out["results"]] == [True, False, False]


def test_resume_journal_is_per_script_and_variables(make_rt):
    rt, adapter = make_rt()
    src = "research(topic)"
    run_script(rt, src, variables={"topic": "a"}, script_id="p.jig")
    out = run_script(rt, src, variables={"topic": "b"}, script_id="p.jig", resume=True)
    assert not out["results"][0]["result"].get("skipped")
    out = run_script(rt, src, variables={"topic": "a"}, script_id="p.jig", resume=True)
    assert out["results"][0]["result"].get("skipped")


# ── shipped examples ────────────────────────────────────────────────────
def test_every_example_script_parses(commands):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "examples"
    for f in root.rglob("*.jig"):
        parse(f.read_text(encoding="utf-8"), set(commands),
              predefined={"id", "goal", "constraints", "topic", "question", "requirements", "max_fixes"})


def test_factory_example_runs_with_fix_loop(make_rt):
    import json
    import re
    from pathlib import Path
    from fixtures import junit_cmd
    root = Path(__file__).resolve().parents[1] / "examples"
    src = (root / "pipelines" / "factory.jig").read_text(encoding="utf-8")
    src = re.sub(r"TEST = \[.*?\]\n", f"TEST = ['{junit_cmd()}']\n", src, flags=re.S)
    src = src.replace(', expect_files=["dist/index.html"]', "")
    variables = json.loads((root / "batches" / "factory.json").read_text(encoding="utf-8"))
    for req in variables["requirements"]:
        req["constraints"] = ["React + TypeScript"]     # the only constraint the fixture spec restates
    rt, adapter = make_rt()
    out = run_script(rt, src, variables=variables)
    assert out["status"] == "completed", out.get("error") or [r["result"].get("error") for r in out["results"]]
    # fixture verify always reports R-03 unsatisfied, so each app gets max_fixes (2) rebuilds
    assert out["log"][:2] == ["TODO-001: fixing 1 gap(s), attempt 1", "TODO-001: fixing 1 gap(s), attempt 2"]
    assert out["executed"] == 2 * (4 + 2 * 3)
    assert '"TODO-001": {"tests": "completed", "verify": "pass"}' in out["log"][-1]
    assert '"NOTE-001"' in out["log"][-1]
    builds = [r.prompt for r in adapter.requests if "`build`" in r.system]
    assert "R-03: no sound" in builds[1]


# ── --continue-on-error: the script decides the outcome ─────────────────
def test_recovered_failure_completes_and_fail_marks_the_run_failed(make_rt):
    rt, _ = make_rt({"research": [FAIL, FAIL, _research("ok")]})
    src = '''
r = research("x")
if r.status == "failed":
    r = research("x", question="again")
if r.status != "completed":
    fail("still failing")
print(r.output.summary)
'''
    out = run_script(rt, src, continue_on_error=True)
    assert out["status"] == "completed" and out["step_failures"] == 1 and out["log"] == ["ok"]
    rt2, _ = make_rt({"research": [FAIL, FAIL, FAIL, FAIL]})
    out = run_script(rt2, src, continue_on_error=True)
    assert out["status"] == "failed" and "fail(): still failing" in out["error"]["message"]
    assert out["error"]["message"].startswith("line 6")


def test_without_continue_on_error_a_failed_step_still_stops_the_script(make_rt):
    rt, adapter = make_rt({"research": [FAIL, FAIL]})
    out = run_script(rt, 'r = research("x")\nresearch("y")\n')
    assert out["status"] == "failed" and out["executed"] == 1


def test_batch_summary_reports_script_outcome():
    from jig.batch import _summarize
    ok = {"status": "completed", "results": [{"line": 1, "result": {"command": "verify", "status": "failed"}},
                                             {"line": 2, "result": {"command": "verify", "status": "completed"}}]}
    assert _summarize(ok, 0, "")["failed_at"] is None
    bad = {"status": "failed", "error": {"message": "line 9: fail(): nope"},
           "results": [{"line": 2, "result": {"command": "verify", "status": "completed"}}]}
    s = _summarize(bad, 1, "")
    assert s["failed_at"] == "script" and "fail(): nope" in s["error"]
