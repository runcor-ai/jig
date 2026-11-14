"""Named agents (agent="luna"), the Codex adapter, and the FACTS spec format (no model calls)."""
import copy
from pathlib import Path

from fixtures import SPEC
from jig.adapters import AgentRequest, ToolPolicy
from jig.adapters.codex import CodexAdapter, parse_json_answer
from jig.prompts import build_spec
from jig.script import run_script

FACTS = """## THINGS
- ball: moving square
## VALUES
- R-02.win_score: 10
## RULES
- R-01: ball bounces off top and bottom walls
- R-02: first to win_score wins
- R-03: sound on hit (could)
## LINKS
- ball -> paddle: bounces off
## TIMING
- loop: 60 frames per second"""


def test_named_agent_is_recorded_and_unknown_agent_fails(make_rt):
    rt, adapter = make_rt()
    out = run_script(rt, 'r = research("passkeys", agent="luna")\nprint(r.status)')
    ex = out["results"][0]["result"]["execution"]
    assert out["status"] == "completed" and ex["agent"] == "luna"
    out = run_script(rt, 'research("passkeys", agent="nobody")')
    err = out["results"][0]["result"]["error"]
    assert err["code"] == "E_PARAM" and "unknown agent 'nobody'" in err["message"] and "luna" in err["message"]


def test_codex_argv_maps_tool_policy_to_sandbox(tmp_path):
    a = CodexAdapter(executable="codex")
    build = AgentRequest(prompt="p", system="s", output_schema={"type": "object"}, cwd=tmp_path, model="gpt-6-luna",
                         policy=ToolPolicy(name="build", tools=["Read", "Write", "Bash"]))
    argv = a.build_argv(build, tmp_path / "last.txt")
    assert argv[:2] == ["codex", "exec"] and "--ignore-user-config" in argv and "--ephemeral" in argv
    assert argv[argv.index("-s") + 1] == "workspace-write" and "sandbox_workspace_write.network_access=true" in argv
    assert argv[argv.index("-m") + 1] == "gpt-6-luna" and 'web_search="disabled"' in argv and argv[-1] == "-"
    read = AgentRequest(prompt="p", system="s", output_schema=None, cwd=tmp_path,
                        policy=ToolPolicy(name="read_workspace", tools=["Read", "Grep"]))
    argv = a.build_argv(read, tmp_path / "last.txt")
    assert argv[argv.index("-s") + 1] == "read-only" and "sandbox_workspace_write.network_access=true" not in argv
    prompt = a.full_prompt(build)
    assert prompt.startswith("s\n\np") and "conforms to this JSON Schema" in prompt


def test_codex_refuses_research_and_parses_answers(tmp_path):
    a = CodexAdapter(executable=__import__("sys").executable)     # any executable that exists
    a.available = lambda: (True, "test")
    r = a.invoke(AgentRequest(prompt="p", system="s", output_schema=None, cwd=tmp_path,
                              policy=ToolPolicy(name="research", tools=["WebSearch", "WebFetch"])))
    assert not r.ok and r.error_code == "E_AGENT_UNAVAILABLE" and "web research" in r.error
    assert parse_json_answer('{"a": 1}') == {"a": 1}
    assert parse_json_answer('Done.\n```json\n{"a": [1, 2]}\n```') == {"a": [1, 2]}
    assert parse_json_answer('Here it is: {"a": {"b": 2}} thanks') == {"a": {"b": 2}}
    assert parse_json_answer("no json here") is None


def test_specify_facts_format_is_checked_and_read_by_build(make_rt):
    good = copy.deepcopy(SPEC)
    good["facts"] = FACTS
    bad = copy.deepcopy(SPEC)
    bad["facts"] = "## THINGS\n- ball: square"              # missing headings and requirement ids
    rt, adapter = make_rt({"specify": [bad, good]})
    out = run_script(rt, 'spec = specify("pong", format="facts")\nbuild(spec)\n')
    assert out["status"] == "completed", out
    spec_res = out["results"][0]["result"]
    assert spec_res["execution"]["attempts"] == 2                  # first answer failed facts_format, then fixed
    first_retry = [r.prompt for r in adapter.requests if "`specify`" in r.system][1]
    assert "facts_format" in first_retry and "no '## VALUES' section" in first_retry
    build_prompt = [r.prompt for r in adapter.requests if "`build`" in r.system][0]
    assert "FACTS format" in build_prompt and "R-02.win_score: 10" in build_prompt
    assert '"acceptance"' not in build_prompt                     # the builder reads the notes, not the prose spec


def test_prose_spec_is_unchanged_for_the_builder():
    assert build_spec(SPEC).startswith("{") and '"requirements"' in build_spec(SPEC)
    s = dict(SPEC, facts=FACTS)
    assert build_spec(s).startswith("Notes (FACTS format") and "- R-01: Ball bounces (must)" in build_spec(s)
