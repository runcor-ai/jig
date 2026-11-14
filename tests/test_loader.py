"""The command loader: built-ins, user and project commands, overrides and definition errors."""
import json
from pathlib import Path

import pytest

from jig.cli import main
from jig.loader import BUILTIN_DIR, CommandDefError, load_commands

ROOT = Path(__file__).resolve().parents[1]


def write_cmd(d: Path, name: str, yaml_text: str, prompt: str | None = "Do $target", schema: dict | None = None):
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.yaml").write_text(yaml_text)
    if prompt is not None:
        (d / f"{name}.md").write_text(prompt)
    if schema is not False:
        (d / f"{name}.schema.json").write_text(json.dumps(schema or {"type": "object"}))


def test_builtins_are_the_small_standard_library():
    cmds = load_commands(ROOT, dirs=[("builtin", BUILTIN_DIR)])
    assert set(cmds) == {"research", "specify", "build", "test", "verify"}
    assert all(c.source == "builtin" for c in cmds.values())
    assert cmds["test"]["mode"] == "procedure" and cmds["build"]["requires"] == ["specify"]


def test_user_and_project_dirs_override_in_order(tmp_path):
    user, proj = tmp_path / "user", tmp_path / "proj"
    write_cmd(user, "summarize", "purpose: user version\n")
    write_cmd(proj, "summarize", "purpose: project version\n")
    write_cmd(proj, "research", "purpose: my research\ntool_policy: none\n")
    cmds = load_commands(tmp_path, dirs=[("builtin", BUILTIN_DIR), ("user", user), ("project", proj)])
    assert cmds["summarize"]["purpose"] == "project version" and cmds["summarize"].overrides == "user"
    assert cmds["research"].source == "project" and cmds["research"].overrides == "builtin"


def test_defaults_and_inline_policy_and_schema(tmp_path):
    write_cmd(tmp_path, "classify", """
purpose: Classify text
parameters:
  labels: {type: list, items: string, default: [a, b]}
tool_policy: {tools: [Read], deny: ["Bash(env:*)"]}
output_schema: {type: object, required: [label], properties: {label: {type: string}}}
""", schema=False)
    c = load_commands(tmp_path, dirs=[("project", tmp_path)])["classify"]
    assert c["target"]["type"] == "artifact_or_text" and c["artifact"] == "optional" and c["idempotent"]
    assert c.schema["required"] == ["label"] and c["tool_policy"]["tools"] == ["Read"]


@pytest.mark.parametrize("yaml_text,prompt,schema,msg", [
    ("tool_policy: none\n", "x", None, "missing 'purpose'"),
    ("purpose: p\nvalidators: [made_up]\n", "x", None, "unknown validator 'made_up'"),
    ("purpose: p\npostprocess: [nope]\n", "x", None, "unknown postprocess hook"),
    ("purpose: p\n", None, None, "needs a prompt template"),
    ("purpose: p\nmode: procedure\nprocedure: rm_rf\n", None, None, "unknown procedure"),
    ("purpose: p\nparameters: {x: {type: banana}}\n", "x", None, "needs type"),
    ("purpose: p\nparameters: {max_attempts: {type: integer}}\n", "x", None, "reserved"),
    ("purpose: p\ntarget: {type: elsewhere}\n", "x", None, "target.type"),
    ("purpose: p\nartifact: use\ntarget: {type: text}\n", "x", None, "artifact: use requires"),
    ("purpose: p\n", "x", {"type": "nonsense"}, "output schema invalid"),
])
def test_invalid_definitions_fail_with_file_and_reason(tmp_path, yaml_text, prompt, schema, msg):
    write_cmd(tmp_path, "bad", yaml_text, prompt, schema)
    with pytest.raises(CommandDefError) as e:
        load_commands(tmp_path, dirs=[("project", tmp_path)])
    assert msg in str(e.value) and "bad.yaml" in str(e.value)


def test_invalid_command_name(tmp_path):
    write_cmd(tmp_path, "Bad-Name", "purpose: p\n")
    with pytest.raises(CommandDefError, match="lowercase"):
        load_commands(tmp_path, dirs=[("project", tmp_path)])


def test_cli_commands_and_check_reflect_loaded_commands(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("JIG_USER_COMMANDS", str(tmp_path / "user"))
    write_cmd(tmp_path / "user", "summarize", "purpose: Summarize a document\ntool_policy: none\n")
    write_cmd(tmp_path / "commands", "tag", "purpose: Tag things\ntool_policy: none\n")
    assert main(["--project", str(tmp_path), "commands"]) == 0
    out = capsys.readouterr().out
    assert "7 commands loaded" in out and "summarize    [user]" in out and "tag          [project]" in out
    main(["--project", str(tmp_path), "check"])
    assert "commands: 7 loaded OK (builtin 5, project 1, user 1)" in capsys.readouterr().out


def test_cli_check_reports_broken_definition(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("JIG_USER_COMMANDS", str(tmp_path / "none"))
    write_cmd(tmp_path / "commands", "broken", "purpose: p\nvalidators: [nope]\n")
    assert main(["--project", str(tmp_path), "check"]) == 1
    assert "INVALID" in capsys.readouterr().out


def test_unknown_tool_policy_is_reported_by_check(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("JIG_USER_COMMANDS", str(tmp_path / "none"))
    write_cmd(tmp_path / "commands", "odd", "purpose: p\ntool_policy: superpowers\n")
    main(["--project", str(tmp_path), "check"])
    assert "superpowers" in capsys.readouterr().out


# ── template placeholders and validator opt-in ──────────────────────────
def test_template_placeholder_typo_is_caught(tmp_path):
    write_cmd(tmp_path, "summarize", "purpose: p\nparameters: {audience: {type: string, default: all}}\n",
              prompt="Summarize $target for $audeince using ${spec} and $$5 budget, costs $5")
    with pytest.raises(CommandDefError) as e:
        load_commands(tmp_path, dirs=[("project", tmp_path)])
    msg = str(e.value)
    assert "undefined placeholder(s) $audeince" in msg and "summarize.md" in msg
    assert "$target" not in msg.split("undefined placeholder(s)")[1].split(";")[0]   # known names not flagged


def test_malformed_brace_placeholder_is_caught(tmp_path):
    write_cmd(tmp_path, "t", "purpose: p\n", prompt="line one\nUse ${target and more")
    with pytest.raises(CommandDefError, match=r"malformed \$\{\.\.\.\} placeholder at line\(s\) \[2\]"):
        load_commands(tmp_path, dirs=[("project", tmp_path)])


def test_context_placeholders_and_literal_dollars_are_fine(tmp_path):
    write_cmd(tmp_path, "t", "purpose: p\n",
              prompt="$command $artifact_id ${target} $parameters $spec $tests $expected_ids $context "
                     "$workspace_state; price $$10 or $5")
    assert "t" in load_commands(tmp_path, dirs=[("project", tmp_path)])


def test_all_shipped_templates_pass_the_placeholder_check():
    cmds = load_commands(ROOT, dirs=[("builtin", BUILTIN_DIR), ("project", ROOT / "commands")])
    assert {"specify", "build", "test", "verify", "research", "review"} <= set(cmds)


def test_user_command_opts_into_builtin_validators(tmp_path):
    write_cmd(tmp_path, "audit", "purpose: p\nvalidators: [findings_cite_existing_files, research_sources_retrieved]\n")
    c = load_commands(tmp_path, dirs=[("user", tmp_path)])["audit"]
    assert c["validators"] == ["findings_cite_existing_files", "research_sources_retrieved"]


def test_review_example_uses_the_citation_validator():
    c = load_commands(ROOT, dirs=[("builtin", BUILTIN_DIR), ("project", ROOT / "commands")])["review"]
    assert "findings_cite_existing_files" in c["validators"] and c.source == "project"


def test_cli_check_reports_template_typo(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("JIG_USER_COMMANDS", str(tmp_path / "none"))
    write_cmd(tmp_path / "commands", "greet", "purpose: p\n", prompt="Hello $nmae")
    assert main(["--project", str(tmp_path), "check"]) == 1
    out = capsys.readouterr().out
    assert "INVALID" in out and "greet.md uses undefined placeholder(s) $nmae" in out
