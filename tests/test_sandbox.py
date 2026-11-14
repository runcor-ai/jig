"""--sandbox docker: argv construction, availability errors, and use by agent and test runner."""
from pathlib import Path

from fixtures import junit_cmd

from jig.adapters import AgentRequest, ClaudeCodeAdapter, ToolPolicy
from jig.sandbox import DockerSandbox, make_sandbox
from jig.script import run_script


def test_wrap_mounts_only_the_workspace_and_passes_token_by_name(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-secret-value")
    sb = DockerSandbox()
    argv = sb.wrap(["claude", "-p"], tmp_path, {"BACKEND_PORT": "20000"})
    mounts = [argv[i + 1] for i, a in enumerate(argv) if a == "-v"]
    assert mounts == [f"{tmp_path.resolve()}:/workspace"]
    assert "CLAUDE_CODE_OAUTH_TOKEN" in argv and not any("sk-secret-value" in a for a in argv)
    assert {"--cap-drop", "ALL", "no-new-privileges", "BACKEND_PORT=20000"} <= set(argv)
    assert argv[-3:] == ["jig-agent:0.1", "claude", "-p"]


def test_adapter_runs_claude_inside_the_container(tmp_path, monkeypatch):
    """Intercept the process the adapter actually launches."""
    import jig.adapters.claude_code as cc
    launched = {}

    class FakeProc:
        def __init__(self, argv, **kw):
            launched["argv"] = argv
            launched["cwd"] = kw.get("cwd")
            import io
            self.stdin, self.stderr, self.returncode = io.StringIO(), io.StringIO(""), 0
            self.stdout = io.StringIO('{"type":"result","subtype":"success","is_error":false,'
                                      '"structured_output":{},"result":"{}"}\n')

        def wait(self):
            return 0

        def kill(self):
            pass

    monkeypatch.setattr(cc.subprocess, "Popen", FakeProc)
    a = ClaudeCodeAdapter(executable="C:/bin/claude.exe")
    monkeypatch.setattr(a, "available", lambda: (True, "stub"))
    req = AgentRequest(prompt="p", system="s", output_schema={"type": "object"}, policy=ToolPolicy("none", []),
                       cwd=tmp_path, sandbox=DockerSandbox())
    assert a.invoke(req).ok
    argv = launched["argv"]
    assert Path(argv[0]).stem.lower() == "docker" and argv[1] == "run"
    i = argv.index("jig-agent:0.1")
    assert argv[i + 1] == "claude" and "C:/bin/claude.exe" not in argv      # in-container claude, not host
    assert "--permission-mode" in argv[i:] and "dontAsk" in argv[i:]         # same permission flags inside


def test_unready_sandbox_reports_unavailable(make_rt, monkeypatch):
    class NotReady(DockerSandbox):
        def check(self):
            return False, "image jig-agent:0.1 not built: run `jig sandbox-build`"
    rt, adapter = make_rt(sandbox=NotReady())
    res = rt.run("specify", "x")
    assert res["status"] == "unavailable" and "sandbox-build" in res["error"]["message"]
    assert not adapter.requests


def test_agent_and_test_runner_use_the_sandbox(make_rt):
    calls = []

    class Passthrough(DockerSandbox):
        """Records what would run in the container, then runs it directly (no docker needed)."""
        def check(self):
            return True, "test"

        def wrap(self, argv, workspace, env=None):
            calls.append((argv[0], Path(workspace).name))
            return argv

    rt, adapter = make_rt(sandbox=Passthrough())
    out = run_script(rt, f'spec = specify("x", id="PONG-001")\nbuild(spec)\ntest(spec, run=[\'{junit_cmd()}\'])\n')
    assert out["status"] == "completed", out
    assert all(r.sandbox is rt.sandbox for r in adapter.requests)           # agent requests carry the sandbox
    assert calls and calls[0][1] == "PONG-001"                              # test command wrapped, in workspace
    assert out["results"][2]["result"]["output"]["sandbox"] == "docker"


def test_make_sandbox():
    assert make_sandbox(None) is None and make_sandbox("none") is None
    assert isinstance(make_sandbox("docker"), DockerSandbox)


def test_root_filesystem_is_read_only_with_writable_tmpfs(tmp_path):
    argv = DockerSandbox().wrap(["true"], tmp_path)
    assert "--read-only" in argv
    tmpfs = [argv[i + 1] for i, a in enumerate(argv) if a == "--tmpfs"]
    assert [t.split(":")[0] for t in tmpfs] == ["/tmp", "/home/node"]      # /home/node covers ~/.npm, ~/.claude
    home = next(t for t in tmpfs if t.startswith("/home/node:"))
    assert "uid=1000" in home and "exec" in home.split(":")[1].split(",")  # npx runs binaries from ~/.npm
    assert argv.index("--read-only") < argv.index("jig-agent:0.1")      # docker options precede the image
