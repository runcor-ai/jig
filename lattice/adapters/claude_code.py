"""Claude Code adapter: runs `claude -p` headless with structured output.

Tool boundaries are enforced by Claude Code itself:
  --tools            which tools exist in the session at all
  --allowedTools     rules auto-approved
  --disallowedTools  rules always denied
  --permission-mode dontAsk   anything not pre-approved is denied (no prompts)
  --setting-sources project   user-level settings/allow-lists are NOT inherited
  --strict-mcp-config         no MCP servers
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from .base import AgentRequest, AgentResponse


class ClaudeCodeAdapter:
    name = "claude_code"

    def __init__(self, executable: str | None = None):
        self.executable = executable or shutil.which("claude")

    def available(self) -> tuple[bool, str]:
        if not self.executable:
            return False, "the `claude` CLI was not found on PATH"
        try:
            out = subprocess.run([self.executable, "--version"], capture_output=True, text=True, timeout=30)
            return out.returncode == 0, out.stdout.strip() or out.stderr.strip()
        except Exception as e:  # pragma: no cover - environment dependent
            return False, f"`claude --version` failed: {e}"

    def build_argv(self, req: AgentRequest) -> list[str]:
        argv = [self.executable, "-p", "--output-format", "stream-json", "--verbose",
                "--no-session-persistence", "--permission-mode", "dontAsk",
                "--setting-sources", "project", "--strict-mcp-config",
                "--tools", ",".join(req.policy.tools)]
        if req.policy.allow:
            argv += ["--allowedTools", *req.policy.allow]
        if req.policy.deny:
            argv += ["--disallowedTools", *req.policy.deny]
        if req.output_schema is not None:
            # Claude Code's schema validator does not resolve the draft-2020-12 meta-schema URI;
            # the runtime still validates the output against the full schema itself.
            schema = {k: v for k, v in req.output_schema.items() if k != "$schema"}
            argv += ["--json-schema", json.dumps(schema, separators=(",", ":"))]
        if req.system:
            argv += ["--append-system-prompt", req.system]
        if req.model:
            argv += ["--model", req.model]
        if req.effort:
            argv += ["--effort", req.effort]
        if req.max_budget_usd:
            argv += ["--max-budget-usd", f"{req.max_budget_usd:.2f}"]
        return argv

    def invoke(self, req: AgentRequest) -> AgentResponse:
        ok, why = self.available()
        if not ok:
            return AgentResponse(ok=False, error_code="E_AGENT_UNAVAILABLE", error=why)
        argv = self.build_argv(req)
        req.cwd.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        events_f = open(req.events_path, "a", encoding="utf-8") if req.events_path else None
        final: dict | None = None
        stderr_chunks: list[str] = []
        try:
            proc = subprocess.Popen(argv, cwd=str(req.cwd), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                                    env={**os.environ, **(req.env or {})})
        except OSError as e:
            return AgentResponse(ok=False, error_code="E_AGENT_UNAVAILABLE", error=str(e))

        def feed():
            try:
                proc.stdin.write(req.prompt)
                proc.stdin.close()
            except OSError:
                pass

        def drain_err():
            for line in proc.stderr:
                stderr_chunks.append(line)

        threading.Thread(target=feed, daemon=True).start()
        threading.Thread(target=drain_err, daemon=True).start()
        timer = threading.Timer(req.timeout_s, proc.kill)
        timer.start()
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                if events_f:
                    events_f.write(line + "\n")
                    events_f.flush()
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if ev.get("type") == "result":
                    final = ev
                elif req.on_event:
                    s = _summarize(ev)
                    if s:
                        req.on_event(s)
            proc.wait()
        finally:
            timed_out = not timer.is_alive() and final is None
            timer.cancel()
            if events_f:
                events_f.close()
        elapsed = int((time.monotonic() - started) * 1000)
        if final is None:
            if timed_out:
                return AgentResponse(ok=False, error_code="E_TIMEOUT", duration_ms=elapsed,
                                     error=f"agent exceeded {req.timeout_s}s and was stopped")
            return AgentResponse(ok=False, error_code="E_AGENT_FAILED", duration_ms=elapsed,
                                 error=f"agent exited {proc.returncode} without a result. "
                                       f"stderr: {''.join(stderr_chunks)[-2000:]}")
        return _to_response(final)


def _summarize(ev: dict) -> str | None:
    if ev.get("type") != "assistant":
        return None
    for block in (ev.get("message") or {}).get("content", []) or []:
        if block.get("type") == "tool_use":
            inp = block.get("input") or {}
            hint = inp.get("file_path") or inp.get("command") or inp.get("pattern") or ""
            return f"{block.get('name')} {str(hint)[:120]}".strip()
    return None


def _to_response(final: dict) -> AgentResponse:
    usage = final.get("usage") or {}
    token_usage = None
    if usage:
        token_usage = {k: usage.get(k) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                                                  "cache_read_input_tokens") if usage.get(k) is not None}
    models = list((final.get("modelUsage") or {}).keys())
    resp = AgentResponse(
        ok=not final.get("is_error") and final.get("subtype") == "success",
        structured_output=final.get("structured_output"),
        text=final.get("result") or "",
        model=",".join(models) if models else None,
        duration_ms=final.get("duration_ms"),
        token_usage=token_usage,
        cost_usd=final.get("total_cost_usd"),
        num_turns=final.get("num_turns"),
        permission_denials=final.get("permission_denials") or [],
        session_id=final.get("session_id"),
    )
    if not resp.ok:
        sub = final.get("subtype") or ""
        resp.error_code = "E_BUDGET" if "budget" in sub else "E_AGENT_FAILED"
        resp.error = f"agent reported {sub or 'error'}: {(final.get('result') or '')[:1000]}"
    elif resp.structured_output is None:
        # Fall back to parsing the text result as JSON (the schema is still enforced by the runtime).
        try:
            resp.structured_output = json.loads(resp.text)
        except (json.JSONDecodeError, TypeError):
            pass
    return resp
