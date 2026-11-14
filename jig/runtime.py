"""Command runtime: normalize -> validate params -> resolve context -> dispatch -> validate output -> persist.

Every command (built-in or user-defined) is a loaded plugin (jig/loader.py) and runs
through `Runtime.execute`. Commands differ only in their definition files.
"""
from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import jsonschema

from . import prompts
from .adapters import AgentRequest, ToolPolicy, make_adapter
from .config import ConfigError, deep_merge, load_config
from .errors import JigError
from .loader import Command, load_commands
from .procedures import POSTPROCESS, PROCEDURES
from .sandbox import make_sandbox
from .store import ID_RE, Store, write_json
from .validators import VALIDATORS, ValidationContext, finding

CONTROL_KEYS = {"approval_required", "max_attempts"}
FILE_TOOLS = {"Read", "Grep", "Glob", "Write", "Edit", "Bash"}
MAX_UNTRUSTED_CHARS = 200_000


@dataclass
class ExecContext:
    command: str
    cmd: Command
    target: Any
    params: dict
    controls: dict
    run_id: str
    run_dir: Path
    artifact_id: str | None = None
    manifest: dict = field(default_factory=dict)
    workspace: Path | None = None
    spec: dict | None = None          # output of the artifact's `specify` stage
    test: dict | None = None          # output of the artifact's `test` stage
    agent_events: Path | None = None  # event log of the latest agent attempt (evidence checks)

    def env(self) -> dict:
        """Per-artifact environment: isolated ports so parallel apps never collide."""
        ports = (self.manifest or {}).get("ports") or {}
        e = {f"{k.upper()}_PORT": str(v) for k, v in ports.items()}
        if self.artifact_id:
            e["JIG_ARTIFACT_ID"] = self.artifact_id
        return e


def _status_for(code: str) -> str:
    if code == "E_MISSING_CONTEXT":
        return "blocked"
    if code in ("E_UNAVAILABLE", "E_AGENT_UNAVAILABLE"):
        return "unavailable"
    return "failed"


class Runtime:
    def __init__(self, project_dir: Path | str, adapter=None, config: dict | None = None,
                 commands: dict[str, Command] | None = None, echo: Callable[[str], None] | None = None,
                 sandbox=None, interactive: bool = False):
        self.project_dir = Path(project_dir).resolve()
        self.config = config or load_config(self.project_dir)
        self.commands = commands if commands is not None else load_commands(self.project_dir)
        self.store = Store(self.project_dir / self.config["store"])
        self.adapter = adapter or make_adapter(self.config["agent"]["adapter"])
        self.sandbox = make_sandbox(sandbox) if isinstance(sandbox, str) or sandbox is None else sandbox
        self.echo = echo

    # ── contract ────────────────────────────────────────────────────────
    def normalize(self, command: str, target: Any = None, kwargs: dict | None = None,
                  context: dict | None = None) -> dict:
        params = dict(kwargs or {})
        controls = {"approval_required": False}
        for k in CONTROL_KEYS:
            if k in params:
                controls[k] = params.pop(k)
        return {"command": command, "target": target, "parameters": params, "context": context or {},
                "controls": controls}

    def run(self, command: str, target: Any = None, /, **kwargs) -> dict:
        return self.execute(self.normalize(command, target, kwargs))

    # ── execute ─────────────────────────────────────────────────────────
    def execute(self, inv: dict) -> dict:
        command = inv.get("command")
        run_id, run_dir = self.store.new_run(str(command))
        write_json(run_dir / "invocation.json", inv)
        result = {"command": command, "status": "failed", "artifact_id": None, "output": None,
                  "validation": {"passed": False, "findings": []},
                  "execution": {"model": None, "duration_ms": None, "token_usage": None, "cost_usd": None,
                                "adapter": None, "attempts": 0, "run_id": run_id, "permission_denials": [],
                                "sandbox": self.sandbox.name if self.sandbox else None},
                  "error": None}
        started = time.monotonic()
        try:
            cmd = self.commands.get(command)
            if cmd is None:
                raise JigError("E_UNKNOWN_COMMAND", f"unknown command '{command}'. Loaded: "
                                                        f"{', '.join(sorted(self.commands))}")
            if inv.get("controls", {}).get("approval_required"):
                raise JigError("E_PARAM", "approval_required is not supported in v0.2 (no gated commands)")
            ctx = self._prepare(inv, cmd, run_id, run_dir)
            result["artifact_id"] = ctx.artifact_id
            self.store.set_run_status(run_dir, state="running", command=command, artifact_id=ctx.artifact_id,
                                      started_at=time.time())
            if self.sandbox:
                ok, why = self.sandbox.check()
                if not ok:
                    raise JigError("E_UNAVAILABLE", f"sandbox unavailable: {why}")
            if cmd["mode"] == "agent":
                output, validation, execution = self._run_agent(ctx)
                result["execution"].update(execution)
            else:
                output = PROCEDURES[cmd["procedure"]](self, ctx)
                validation = self.validate_output(cmd, output, ctx)
            findings = list(validation["findings"])
            for hook in cmd["postprocess"]:
                findings = POSTPROCESS[hook](self, ctx, output, findings)
            validation = {"passed": not any(f["severity"] == "error" for f in findings), "findings": findings}
            result["output"] = output
            result["validation"] = validation
            result["status"] = "completed" if validation["passed"] else "failed"
            if not validation["passed"]:
                result["error"] = {"code": "E_SCHEMA" if any(f["rule"] == "schema" for f in findings)
                                   else "E_VALIDATION", "message": "output failed validation; see findings"}
            if cmd["artifact"] == "create" and output is not None:
                ctx.artifact_id = self._create_artifact(ctx, output)
                result["artifact_id"] = ctx.artifact_id
            if ctx.artifact_id and output is not None:
                self.store.record_stage(ctx.artifact_id, command, run_id, result["status"], output,
                                        {**validation, "params": ctx.params}, result["execution"].get("cost_usd"))
        except JigError as e:
            result["status"] = _status_for(e.code)
            result["error"] = e.to_dict()
        except ConfigError as e:
            result["error"] = {"code": "E_PARAM", "message": str(e)}
        result["execution"]["duration_ms_wall"] = int((time.monotonic() - started) * 1000)
        write_json(run_dir / "result.json", result)
        self.store.set_run_status(run_dir, state="finished", status=result["status"])
        self.store.append_log({"run_id": run_id, "command": command, "artifact_id": result["artifact_id"],
                               "status": result["status"], "error": result["error"],
                               "validation_passed": result["validation"]["passed"],
                               "findings": len(result["validation"]["findings"]),
                               "cost_usd": result["execution"].get("cost_usd"),
                               "duration_ms": result["execution"].get("duration_ms")})
        return result

    # ── preparation ────────────────────────────────────────────────────
    def _prepare(self, inv: dict, cmd: Command, run_id: str, run_dir: Path) -> ExecContext:
        params = self._validate_params(cmd, inv.get("parameters") or {})
        ctx = ExecContext(cmd.name, cmd, inv.get("target"), params, dict(inv.get("controls") or {}), run_id,
                          run_dir)
        self._resolve_target(ctx, inv.get("context") or {})
        if ctx.artifact_id:
            ctx.manifest = self.store.manifest(ctx.artifact_id)
            for stage in cmd["requires"]:
                st = ctx.manifest["stages"].get(stage)
                if not st:
                    raise JigError("E_MISSING_CONTEXT", f"{cmd.name} requires stage '{stage}' of "
                                                            f"{ctx.artifact_id}, which has not run")
                if st["status"] != "completed":
                    raise JigError("E_MISSING_CONTEXT", f"{cmd.name} requires stage '{stage}' of "
                                                            f"{ctx.artifact_id}, whose last run ended "
                                                            f"'{st['status']}'")
            ctx.spec = self.store.stage_output(ctx.artifact_id, "specify")
            ctx.test = self.store.stage_output(ctx.artifact_id, "test")
            ctx.workspace = self._workspace(ctx)
        return ctx

    def _validate_params(self, cmd: Command, given: dict) -> dict:
        schema = cmd["parameters"]
        unknown = [k for k in given if k not in schema]
        if unknown:
            raise JigError("E_PARAM", f"{cmd.name}: unknown parameter(s) {unknown}; accepted: "
                                          f"{sorted(schema) or 'none'}")
        out = {}
        for name, ps in schema.items():
            if name not in given:
                out[name] = copy.deepcopy(ps.get("default"))
                continue
            v = given[name]
            if v is None:
                out[name] = None
                continue
            t = ps["type"]
            ok = {"string": isinstance(v, str), "path": isinstance(v, str),
                  "integer": isinstance(v, int) and not isinstance(v, bool),
                  "number": isinstance(v, (int, float)) and not isinstance(v, bool),
                  "boolean": isinstance(v, bool), "list": isinstance(v, list), "object": isinstance(v, dict)}[t]
            if not ok:
                raise JigError("E_PARAM", f"{cmd.name}: parameter '{name}' must be {t}, got {type(v).__name__}")
            if t == "list" and ps.get("items") == "string" and not all(isinstance(x, str) for x in v):
                raise JigError("E_PARAM", f"{cmd.name}: parameter '{name}' must be a list of strings")
            if "enum" in ps and v not in ps["enum"]:
                raise JigError("E_PARAM", f"{cmd.name}: parameter '{name}' must be one of {ps['enum']}")
            if t == "path":
                self._safe_path(v)
            out[name] = v
        return out

    def _safe_path(self, rel: str) -> Path:
        p = (self.project_dir / rel).resolve()
        try:
            p.relative_to(self.project_dir)
        except ValueError:
            raise JigError("E_PARAM", f"path '{rel}' is outside the project directory") from None
        if not p.is_file():
            raise JigError("E_PARAM", f"file '{rel}' does not exist")
        return p

    def read_untrusted(self, rel: str) -> str:
        text = self._safe_path(rel).read_text(encoding="utf-8", errors="replace")
        return text[:MAX_UNTRUSTED_CHARS].replace("</data>", "&lt;/data&gt;")

    def _resolve_target(self, ctx: ExecContext, context: dict) -> None:
        spec, t = ctx.cmd["target"], ctx.target
        kind = spec["type"]
        if kind == "none":
            if t is not None:
                raise JigError("E_PARAM", f"{ctx.command} takes no target")
        elif t is None:
            if spec.get("required"):
                raise JigError("E_PARAM", f"{ctx.command} requires a target")
        elif not isinstance(t, str):
            raise JigError("E_PARAM", f"{ctx.command}: target must be a string or an artifact")
        elif kind == "artifact" or (kind == "artifact_or_text" and ID_RE.match(t)):
            if not self.store.exists(t):
                raise JigError("E_UNKNOWN_ARTIFACT", f"artifact '{t}' does not exist. Known: "
                                                         f"{', '.join(self.store.list_ids()) or 'none'}")
            ctx.artifact_id = t
        elif not t.strip():
            raise JigError("E_PARAM", f"{ctx.command}: target text is empty")
        if ctx.cmd["artifact"] == "create":
            declared = ctx.params.get("id") or context.get("declared_id")
            if declared:
                if not ID_RE.match(declared):
                    raise JigError("E_PARAM", f"artifact id '{declared}' must look like ABC-001")
                if self.store.exists(declared):
                    raise JigError("E_ARTIFACT_EXISTS", f"artifact {declared} already exists")
            ctx.manifest = {"declared_id": declared}

    def _uses_workspace(self, cmd: Command) -> bool:
        return bool(FILE_TOOLS & set(self.tool_policy(cmd).tools))

    def _workspace(self, ctx: ExecContext) -> Path:
        m = ctx.manifest
        if ctx.params.get("path") and ctx.cmd["parameters"].get("path"):
            ws = (self.project_dir / ctx.params["path"]).resolve()
            try:
                ws.relative_to(self.project_dir)
            except ValueError:
                raise JigError("E_PARAM", "path must be inside the project directory") from None
        elif m.get("workspace"):
            ws = self.project_dir / m["workspace"]
        else:
            ws = self.project_dir / self.config["workspace_root"] / ctx.artifact_id
        rel = ws.relative_to(self.project_dir).as_posix()
        writes = {"Write", "Edit", "Bash"} & set(self.tool_policy(ctx.cmd).tools)
        if writes and m.get("workspace") != rel:
            m = self.store.update_manifest(ctx.artifact_id, workspace=rel)
            ctx.manifest = m
        elif self._uses_workspace(ctx.cmd) and not writes and not ws.exists():
            raise JigError("E_MISSING_CONTEXT", f"workspace {ws} does not exist")
        return ws

    def _create_artifact(self, ctx: ExecContext, output: dict) -> str:
        aid = ctx.manifest.get("declared_id")
        code = output.get("artifact_code") if isinstance(output, dict) else None
        if not (isinstance(code, str) and code.isalpha() and code.isupper() and 2 <= len(code) <= 6):
            code = "ART"
        try:
            m = self.store.create_artifact(aid, ctx.target, {"created_by_run": ctx.run_id,
                                                             "command": ctx.command}, code=code)
        except FileExistsError as e:  # another worker claimed the declared id meanwhile
            raise JigError("E_ARTIFACT_EXISTS", str(e)) from None
        ctx.manifest = m
        return m["id"]

    # ── agent execution ─────────────────────────────────────────────────
    def agent_settings(self, cmd: Command) -> dict:
        a = self.config["agent"]
        over = (a.get("overrides") or {}).get(cmd.name, {})
        s = deep_merge({k: v for k, v in a.items() if k != "overrides"}, over)
        if cmd.get("timeout_s") and "timeout_s" not in over:
            s["timeout_s"] = cmd["timeout_s"]
        return s

    def tool_policy(self, cmd: Command) -> ToolPolicy:
        pol = cmd["tool_policy"]
        if isinstance(pol, dict):
            return ToolPolicy(name=f"{cmd.name}:inline", tools=list(pol.get("tools", [])),
                              allow=list(pol.get("allow", [])), deny=list(pol.get("deny", [])))
        p = self.config["tool_policies"].get(pol)
        if p is None:
            raise ConfigError(f"command '{cmd.name}' uses tool policy '{pol}', which is not defined "
                              f"(known: {', '.join(sorted(self.config['tool_policies']))})")
        return ToolPolicy(name=pol, tools=list(p.get("tools", [])), allow=list(p.get("allow", [])),
                          deny=list(p.get("deny", [])))

    def progress(self, ctx: ExecContext, msg: str) -> None:
        self.store.set_run_status(ctx.run_dir, last_event=msg)
        if self.echo:
            self.echo(f"    · {msg}")

    def invoke_agent(self, ctx: ExecContext, label: str, feedback: str | None = None):
        system, prompt = prompts.render(self, ctx)
        if feedback:
            prompt += "\n\n" + feedback
        policy = self.tool_policy(ctx.cmd)
        if self._uses_workspace(ctx.cmd) and ctx.workspace is not None:
            cwd = ctx.workspace
        else:
            cwd = ctx.run_dir / "sandbox"   # empty dir: agents without workspace access see nothing
        s = self.agent_settings(ctx.cmd)
        (ctx.run_dir / f"prompt-{label}.md").write_text(f"<!-- system -->\n{system}\n<!-- prompt -->\n{prompt}",
                                                        encoding="utf-8")
        req = AgentRequest(prompt=prompt, system=system, output_schema=ctx.cmd.schema, policy=policy, cwd=cwd,
                           model=s.get("model"), effort=s.get("effort"), timeout_s=int(s.get("timeout_s", 1200)),
                           env=ctx.env(), sandbox=self.sandbox,
                           events_path=ctx.run_dir / f"agent-events-{label}.jsonl",
                           on_event=lambda m: self.progress(ctx, m), label=label)
        return self.adapter.invoke(req)

    def _run_agent(self, ctx: ExecContext) -> tuple[Any, dict, dict]:
        cmd = ctx.cmd
        max_attempts = int(ctx.controls.get("max_attempts") or
                           (self.config["retries"]["max_attempts"] if cmd["idempotent"] else 1))
        execution = {"model": None, "duration_ms": None, "token_usage": None, "cost_usd": None,
                     "adapter": self.adapter.name, "attempts": 0, "permission_denials": []}
        feedback, output, validation = None, None, {"passed": False, "findings": []}
        for attempt in range(1, max_attempts + 1):
            execution["attempts"] = attempt
            self.progress(ctx, f"agent attempt {attempt}/{max_attempts}")
            resp = self.invoke_agent(ctx, f"a{attempt}", feedback)
            ctx.agent_events = ctx.run_dir / f"agent-events-a{attempt}.jsonl"
            _accumulate(execution, resp)
            if not resp.ok:
                if attempt < max_attempts and resp.error_code == "E_AGENT_FAILED" and cmd["idempotent"]:
                    feedback = None
                    continue
                raise JigError(resp.error_code or "E_AGENT_FAILED", resp.error or "agent failed",
                                   {"attempts": attempt, "execution": execution})
            output = resp.structured_output
            validation = self.validate_output(cmd, output, ctx)
            if validation["passed"]:
                break
            errs = [f for f in validation["findings"] if f["severity"] == "error"]
            feedback = ("## Your previous output failed automated validation\n"
                        "Fix every problem below and return the complete corrected output.\n" +
                        "\n".join(f"- [{f['rule']}] {f['message']}" for f in errs) +
                        "\n\nPrevious output:\n<data name=\"previous_output\">" +
                        json.dumps(output, ensure_ascii=False)[:60_000] + "</data>")
        return output, validation, execution

    # ── validation ─────────────────────────────────────────────────────
    def validate_output(self, cmd: Command, output: Any, ctx: ExecContext) -> dict:
        findings = []
        if output is None:
            findings.append(finding("schema", "agent returned no structured output"))
        else:
            v = jsonschema.Draft202012Validator(cmd.schema)
            for err in sorted(v.iter_errors(output), key=lambda e: list(e.absolute_path))[:25]:
                path = "/".join(str(x) for x in err.absolute_path) or "(root)"
                findings.append(finding("schema", f"{path}: {err.message[:300]}"))
        if not findings:
            vctx = ValidationContext(command=cmd.name, output=output, params=ctx.params, workspace=ctx.workspace,
                                     spec=ctx.spec, test=ctx.test, extra={"agent_events": ctx.agent_events})
            for name in cmd["validators"]:
                try:
                    findings += VALIDATORS[name](vctx)
                except Exception as e:  # a crashing validator is a failed check, never a pass
                    findings.append(finding(name, f"validator crashed: {type(e).__name__}: {e}"))
        return {"passed": not any(f["severity"] == "error" for f in findings), "findings": findings}


def _accumulate(execution: dict, resp) -> None:
    if resp.model:
        execution["model"] = resp.model
    for key, val in (("duration_ms", resp.duration_ms), ("cost_usd", resp.cost_usd)):
        if val is not None:
            execution[key] = round((execution.get(key) or 0) + val, 6)
    if resp.token_usage:
        tu = execution.get("token_usage") or {}
        for k, v in resp.token_usage.items():
            tu[k] = (tu.get(k) or 0) + v
        execution["token_usage"] = tu
    execution["permission_denials"] = (execution.get("permission_denials") or []) + list(resp.permission_denials)
