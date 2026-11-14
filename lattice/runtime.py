"""Command runtime: normalize -> validate -> resolve context -> dispatch -> validate output -> persist.

All 32 commands go through `Runtime.execute`. Commands differ only by their
registry entry (parameters, required stages, schema, tool policy, validators).
"""
from __future__ import annotations

import copy
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import jsonschema

from . import prompts
from .adapters import AgentRequest, ToolPolicy, make_adapter
from .config import ConfigError, deep_merge, load_config, load_registry
from .errors import LatticeError
from .procedures import NATIVE, PROCEDURES
from .profiles import ProfileError, resolve_profile, resolve_stack
from .store import ID_RE, Store, read_json, write_json
from .validators import VALIDATORS, ValidationContext, finding

CONTROL_KEYS = {"approval_required", "max_attempts"}
WORKSPACE_POLICIES = {"read_workspace", "build", "docs"}
MAX_UNTRUSTED_CHARS = 200_000


@dataclass
class ExecContext:
    command: str
    spec: dict
    target: Any
    params: dict
    controls: dict
    run_id: str
    run_dir: Path
    artifact_id: str | None = None
    manifest: dict = field(default_factory=dict)
    workspace: Path | None = None
    profile: dict | None = None
    stack: dict | None = None
    requirement: dict | None = None
    design: dict | None = None
    test: dict | None = None
    decision_model: dict | None = None
    prompt_override: str | None = None
    agent_events: Path | None = None   # event log of the latest agent attempt (for evidence checks)


    def env(self) -> dict:
        """Per-artifact environment: isolated ports and compose project for parallel apps."""
        ports = (self.manifest or {}).get("ports") or {}
        e = {f"{k.upper()}_PORT": str(v) for k, v in ports.items()}
        if self.artifact_id:
            e["COMPOSE_PROJECT_NAME"] = self.artifact_id.lower()
        return e


def _status_for(code: str) -> str:
    if code in ("E_MISSING_CONTEXT", "E_APPROVAL_REQUIRED"):
        return "blocked" if code == "E_MISSING_CONTEXT" else "awaiting_approval"
    if code in ("E_UNAVAILABLE", "E_AGENT_UNAVAILABLE"):
        return "unavailable"
    return "failed"


class Runtime:
    def __init__(self, project_dir: Path | str, adapter=None, interactive: bool = False,
                 config: dict | None = None, registry=None, echo: Callable[[str], None] | None = None):
        self.project_dir = Path(project_dir).resolve()
        self.config = config or load_config(self.project_dir)
        self.registry = registry or load_registry()
        self.store = Store(self.project_dir / self.config["store"])
        self.adapter = adapter or make_adapter(self.config["agent"]["adapter"])
        self.interactive = interactive
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
                                "adapter": None, "attempts": 0, "run_id": run_id, "permission_denials": []},
                  "error": None}
        started = time.monotonic()
        ctx = None
        try:
            spec = self.registry.commands.get(command)
            if spec is None:
                raise LatticeError("E_UNKNOWN_COMMAND", f"unknown command '{command}'")
            ctx = self._prepare(inv, spec, run_id, run_dir)
            result["artifact_id"] = ctx.artifact_id
            self.store.set_run_status(run_dir, state="running", command=command, artifact_id=ctx.artifact_id,
                                      started_at=time.time())
            self._check_approval(ctx)
            mode = spec["execution"]["mode"]
            if mode == "agent":
                output, validation, execution = self._run_agent(ctx)
                result["execution"].update(execution)
            elif mode == "procedure":
                output = PROCEDURES[spec["execution"]["procedure"]](self, ctx)
                validation = self.validate_output(command, output, ctx, ctx.params)
            else:
                output = NATIVE[spec["execution"]["procedure"]](self, ctx)
                validation = {"passed": True, "findings": []}
            output, validation = self._postprocess(ctx, output, validation, result["execution"])
            result["output"] = output
            result["validation"] = validation
            result["status"] = "completed" if validation["passed"] else "failed"
            if not validation["passed"]:
                result["error"] = {"code": "E_SCHEMA" if any(f["rule"] == "schema" for f in validation["findings"])
                                   else "E_VALIDATION", "message": "output failed validation; see findings"}
            if spec["artifact"] == "create" and output is not None:
                ctx.artifact_id = self._create_artifact(ctx, output)
                result["artifact_id"] = ctx.artifact_id
            if ctx.artifact_id and mode in ("agent", "procedure") and output is not None:
                self.store.record_stage(ctx.artifact_id, command, run_id, result["status"], output,
                                        {**validation, "params": ctx.params}, result["execution"].get("cost_usd"))
        except LatticeError as e:
            result["status"] = _status_for(e.code)
            result["error"] = e.to_dict()
        except (ConfigError, ProfileError) as e:
            result["status"] = "failed"
            result["error"] = {"code": getattr(e, "code", "E_PARAM"), "message": str(e)}
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
    def _prepare(self, inv: dict, spec: dict, run_id: str, run_dir: Path) -> ExecContext:
        command = inv["command"]
        params = self._validate_params(command, spec, inv.get("parameters") or {})
        controls = {**{"approval_required": False}, **(inv.get("controls") or {})}
        ctx = ExecContext(command, spec, inv.get("target"), params, controls, run_id, run_dir)
        self._resolve_target(ctx, inv.get("context") or {})
        if ctx.artifact_id:
            ctx.manifest = self.store.manifest(ctx.artifact_id)
            ctx.profile, ctx.stack = ctx.manifest.get("profile"), ctx.manifest.get("stack")
            for stage in spec.get("requires", []):
                st = ctx.manifest["stages"].get(stage)
                if not st:
                    raise LatticeError("E_MISSING_CONTEXT", f"{command} requires stage '{stage}' of "
                                                            f"{ctx.artifact_id}, which has not run")
                if st["status"] != "completed":
                    raise LatticeError("E_MISSING_CONTEXT", f"{command} requires stage '{stage}' of "
                                                            f"{ctx.artifact_id}, whose last run {st['run_id']} "
                                                            f"ended '{st['status']}'")
            ctx.requirement = self.store.stage_output(ctx.artifact_id, "requirement")
            ctx.design = self.store.stage_output(ctx.artifact_id, "design")
            ctx.test = self.store.stage_output(ctx.artifact_id, "test")
            ctx.workspace = self._workspace(ctx)
        elif spec["artifact"] == "create":
            ctx.profile = resolve_profile(self.registry, params.get("standard"), params.get("overrides"))
            ctx.stack = resolve_stack(self.registry, params.get("stack") or [])
        if "decision_model" in params and params["decision_model"]:
            name = params["decision_model"]
            dm = self.registry.decision_models.get(name)
            if not dm:
                raise LatticeError("E_DECISION_MODEL", f"unknown decision model '{name}'. Available: "
                                                       f"{', '.join(sorted(self.registry.decision_models))}")
            ctx.decision_model = {"name": name, **copy.deepcopy(dm)}
        return ctx

    def _validate_params(self, command: str, spec: dict, given: dict) -> dict:
        schema = spec.get("parameters") or {}
        unknown = [k for k in given if k not in schema]
        if unknown:
            raise LatticeError("E_PARAM", f"{command}: unknown parameter(s) {unknown}; accepted: "
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
            ok = {
                "string": isinstance(v, str), "profile": isinstance(v, str), "path": isinstance(v, str),
                "integer": isinstance(v, int) and not isinstance(v, bool),
                "number": isinstance(v, (int, float)) and not isinstance(v, bool),
                "boolean": isinstance(v, bool), "list": isinstance(v, list), "object": isinstance(v, dict),
            }.get(t)
            if ok is None:
                raise ConfigError(f"{command}.{name}: unknown parameter type {t}")
            if not ok:
                raise LatticeError("E_PARAM", f"{command}: parameter '{name}' must be {t}, got {type(v).__name__}")
            if t == "list" and ps.get("items") == "string" and not all(isinstance(x, str) for x in v):
                raise LatticeError("E_PARAM", f"{command}: parameter '{name}' must be a list of strings")
            if "enum" in ps and v not in ps["enum"]:
                raise LatticeError("E_PARAM", f"{command}: parameter '{name}' must be one of {ps['enum']}")
            if t == "path":
                self._safe_path(v)
            out[name] = v
        return out

    def _safe_path(self, rel: str) -> Path:
        p = (self.project_dir / rel).resolve()
        try:
            p.relative_to(self.project_dir)
        except ValueError:
            raise LatticeError("E_PARAM", f"path '{rel}' is outside the project directory") from None
        if not p.is_file():
            raise LatticeError("E_PARAM", f"file '{rel}' does not exist")
        return p

    def read_untrusted(self, rel: str) -> str:
        text = self._safe_path(rel).read_text(encoding="utf-8", errors="replace")
        return text[:MAX_UNTRUSTED_CHARS].replace("</data>", "&lt;/data&gt;")

    def _resolve_target(self, ctx: ExecContext, context: dict) -> None:
        spec, t = ctx.spec, ctx.target
        kind = spec["target"]["type"]
        if t is None:
            if spec["target"].get("required"):
                raise LatticeError("E_PARAM", f"{ctx.command} requires a target")
            return
        if not isinstance(t, str):
            raise LatticeError("E_PARAM", f"{ctx.command}: target must be a string")
        if kind == "artifact" or (kind == "artifact_or_text" and ID_RE.match(t)):
            if not self.store.exists(t):
                raise LatticeError("E_UNKNOWN_ARTIFACT", f"artifact '{t}' does not exist. Known: "
                                                         f"{', '.join(self.store.list_ids()) or 'none'}")
            ctx.artifact_id = t
        elif kind == "text" and not t.strip():
            raise LatticeError("E_PARAM", f"{ctx.command}: target text is empty")
        if spec["artifact"] == "create":
            declared = ctx.params.get("id") or context.get("declared_id")
            if declared:
                if not ID_RE.match(declared):
                    raise LatticeError("E_PARAM", f"artifact id '{declared}' must look like ABC-001")
                if self.store.exists(declared):
                    raise LatticeError("E_ARTIFACT_EXISTS", f"artifact {declared} already exists")
            ctx.manifest = {"declared_id": declared}

    def _workspace(self, ctx: ExecContext) -> Path:
        m = ctx.manifest
        policy = ctx.spec["execution"].get("tool_policy")
        if ctx.spec["execution"].get("workspace") == "prototype":
            return self.project_dir / self.config["workspace_root"] / f"{ctx.artifact_id}-prototype"
        if ctx.command == "build" and ctx.params.get("path"):
            ws = (self.project_dir / ctx.params["path"]).resolve()
            try:
                ws.relative_to(self.project_dir)
            except ValueError:
                raise LatticeError("E_PARAM", "build path must be inside the project directory") from None
        elif m.get("workspace"):
            ws = self.project_dir / m["workspace"]
        else:
            ws = self.project_dir / self.config["workspace_root"] / ctx.artifact_id
        if ctx.command == "build" and m.get("workspace") != ws.relative_to(self.project_dir).as_posix():
            m["workspace"] = ws.relative_to(self.project_dir).as_posix()
            self.store.save_manifest(m)
        if policy in WORKSPACE_POLICIES and ctx.command != "build" and ctx.spec["artifact"] == "use" \
                and "build" in ctx.spec.get("requires", []) and not ws.exists():
            raise LatticeError("E_MISSING_CONTEXT", f"workspace {ws} does not exist")
        return ws

    def _check_approval(self, ctx: ExecContext) -> None:
        if not (ctx.spec["controls"].get("approval_required") or ctx.controls.get("approval_required")):
            return
        if not ctx.artifact_id:
            raise LatticeError("E_APPROVAL_REQUIRED", f"{ctx.command} requires approval but has no artifact")
        if not self.store.consume_approval(ctx.artifact_id, ctx.command):
            raise LatticeError("E_APPROVAL_REQUIRED",
                               f"{ctx.command} on {ctx.artifact_id} requires approval. A person must run "
                               f"`lattice approve {ctx.artifact_id} {ctx.command}` first.")

    def _create_artifact(self, ctx: ExecContext, output: dict) -> str:
        aid = ctx.manifest.get("declared_id")
        code = output.get("artifact_code") if isinstance(output, dict) else None
        if not (isinstance(code, str) and code.isalpha() and code.isupper() and 2 <= len(code) <= 6):
            code = "ART"
        try:
            m = self.store.create_artifact(aid, ctx.target, {"profile": ctx.profile, "stack": ctx.stack,
                                                             "registry_version": self.registry.version,
                                                             "created_by_run": ctx.run_id}, code=code)
        except FileExistsError as e:  # another worker claimed the declared id meanwhile
            raise LatticeError("E_ARTIFACT_EXISTS", str(e)) from None
        ctx.manifest = m
        return m["id"]


    # ── agent execution ─────────────────────────────────────────────────
    def agent_settings(self, command: str, params: dict) -> dict:
        a = self.config["agent"]
        s = deep_merge({k: v for k, v in a.items() if k != "overrides"}, (a.get("overrides") or {}).get(command, {}))
        return s

    def tool_policy(self, name: str) -> ToolPolicy:
        pol = self.config["tool_policies"].get(name)
        if pol is None:
            raise ConfigError(f"tool policy '{name}' is not defined in lattice.yaml")
        return ToolPolicy(name=name, tools=list(pol.get("tools", [])), allow=list(pol.get("allow", [])),
                          deny=list(pol.get("deny", [])))

    def progress(self, ctx: ExecContext, msg: str) -> None:
        self.store.set_run_status(ctx.run_dir, last_event=msg)
        if self.echo:
            self.echo(f"    · {msg}")

    def invoke_agent(self, ctx: ExecContext, schema: dict, policy_name: str, label: str,
                     feedback: str | None = None) -> Any:
        system, prompt = prompts.render(self, ctx)
        if feedback:
            prompt += "\n\n" + feedback
        policy = self.tool_policy(policy_name)
        if policy_name in WORKSPACE_POLICIES and ctx.workspace is not None:
            cwd = ctx.workspace
        else:
            cwd = ctx.run_dir / "sandbox"   # empty dir: agents without workspace access see nothing
        s = self.agent_settings(ctx.command, ctx.params)
        (ctx.run_dir / f"prompt-{label}.md").write_text(f"<!-- system -->\n{system}\n<!-- prompt -->\n{prompt}",
                                                        encoding="utf-8")
        req = AgentRequest(prompt=prompt, system=system, output_schema=schema, policy=policy, cwd=cwd,
                           model=s.get("model"), effort=s.get("effort"), timeout_s=int(s.get("timeout_s", 1200)),
                           env=ctx.env(),
                           events_path=ctx.run_dir / f"agent-events-{label}.jsonl",
                           on_event=lambda m: self.progress(ctx, m), label=label)
        return self.adapter.invoke(req)

    def _run_agent(self, ctx: ExecContext) -> tuple[Any, dict, dict]:
        spec = ctx.spec
        schema = self.registry.schema(spec["output_schema"])
        max_attempts = int(ctx.controls.get("max_attempts") or
                           (self.config["retries"]["max_attempts"] if spec.get("idempotent") else 1))
        execution = {"model": None, "duration_ms": None, "token_usage": None, "cost_usd": None,
                     "adapter": self.adapter.name, "attempts": 0, "permission_denials": []}
        feedback, output, validation = None, None, {"passed": False, "findings": []}
        for attempt in range(1, max_attempts + 1):
            execution["attempts"] = attempt
            self.progress(ctx, f"agent attempt {attempt}/{max_attempts}")
            resp = self.invoke_agent(ctx, schema, spec["execution"]["tool_policy"], f"a{attempt}", feedback)
            ctx.agent_events = ctx.run_dir / f"agent-events-a{attempt}.jsonl"
            _accumulate(execution, resp)
            if not resp.ok:
                if attempt < max_attempts and resp.error_code == "E_AGENT_FAILED" and spec.get("idempotent"):
                    feedback = None
                    continue
                raise LatticeError(resp.error_code or "E_AGENT_FAILED", resp.error or "agent failed",
                                   {"attempts": attempt, "execution": execution})
            output = resp.structured_output
            validation = self.validate_output(ctx.command, output, ctx, ctx.params)
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
    def validate_output(self, command: str, output: Any, ctx: ExecContext, params: dict) -> dict:
        spec = self.registry.commands[command]
        findings = []
        schema = self.registry.schema(spec["output_schema"])
        if output is None:
            findings.append(finding("schema", "agent returned no structured output"))
        else:
            v = jsonschema.Draft202012Validator(schema)
            for err in sorted(v.iter_errors(output), key=lambda e: list(e.absolute_path))[:25]:
                path = "/".join(str(x) for x in err.absolute_path) or "(root)"
                findings.append(finding("schema", f"{path}: {err.message[:300]}"))
        if not findings:
            vctx = ValidationContext(command=command, output=output, params=params, workspace=ctx.workspace,
                                     profile=ctx.profile, stack=ctx.stack, requirement=ctx.requirement,
                                     design=ctx.design, test=ctx.test, decision_model=ctx.decision_model,
                                     extra={"agent_events": ctx.agent_events})
            if command == "requirement":
                vctx.requirement = output
            for name in spec.get("validators", []):
                try:
                    findings += VALIDATORS[name](vctx)
                except Exception as e:  # a crashing validator is a failed check, never a pass
                    findings.append(finding(name, f"validator crashed: {type(e).__name__}: {e}"))
        return {"passed": not any(f["severity"] == "error" for f in findings), "findings": findings}

    # ── command-specific post-processing (deterministic) ────────────────
    def _postprocess(self, ctx: ExecContext, output: Any, validation: dict, execution: dict):
        findings = list(validation["findings"])
        if ctx.command == "test" and isinstance(output, dict):
            if not output.get("passed"):
                failed = [s["name"] for s in output.get("suites", []) if s["status"] != "passed"]
                findings.append(finding("tests_passed", f"suites not passing: {failed}; "
                                                        f"{len(output.get('failed_cases', []))} failing cases"))
                if ctx.params.get("diagnose") and output.get("failed_cases"):
                    ctx.prompt_override = "diagnose"
                    resp = self.invoke_agent(ctx, self.registry.schema("generic_analysis"), "read_workspace",
                                             "diagnose")
                    _accumulate(execution, resp)
                    execution["adapter"] = self.adapter.name
                    output["diagnosis"] = resp.structured_output if resp.ok else {"error": resp.error}
        if ctx.command == "verify" and isinstance(output, dict) and validation["passed"]:
            output["verdict"] = compute_verdict(ctx.requirement, output, ctx.test)
            if output["verdict"]["result"] != "pass":
                findings.append(finding("verification_verdict", "; ".join(output["verdict"]["reasons"])))
        passed = not any(f["severity"] == "error" for f in findings)
        return output, {"passed": passed, "findings": findings}


def compute_verdict(req: dict | None, verify_out: dict, test: dict | None) -> dict:
    """Deterministic verdict; the agent's per-item statuses are inputs, not the verdict itself."""
    status = {i["id"]: i["status"] for i in verify_out.get("items", [])}
    must = [r["id"] for r in (req or {}).get("functional_requirements", []) if r["priority"] == "must"]
    acs = [a["id"] for a in (req or {}).get("acceptance_criteria", [])]
    reasons = []
    unmet_must = [i for i in must if status.get(i) != "satisfied"]
    unmet_ac = [i for i in acs if status.get(i) != "satisfied"]
    if unmet_must:
        reasons.append(f"must requirements not satisfied: {', '.join(f'{i}={status.get(i)}' for i in unmet_must)}")
    if unmet_ac:
        reasons.append(f"acceptance criteria not satisfied: {', '.join(f'{i}={status.get(i)}' for i in unmet_ac)}")
    if test is None:
        reasons.append("no recorded test results")
    elif not test.get("passed"):
        reasons.append("recorded test run did not pass")
    counts: dict[str, int] = {}
    for s in status.values():
        counts[s] = counts.get(s, 0) + 1
    return {"result": "pass" if not reasons else "fail", "reasons": reasons, "status_counts": counts,
            "must_requirements": len(must), "acceptance_criteria": len(acs),
            "tests_passed": None if test is None else bool(test.get("passed"))}


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
