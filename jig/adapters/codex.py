"""Codex adapter: runs `codex exec` headless (for example GPT-6 Luna on a ChatGPT subscription).

Tool boundaries are enforced by Codex's own sandbox, mapped from the command's tool policy:
  no write tools (none, read_workspace)   -s read-only
  write or Bash tools (write_workspace, build)
                                          -s workspace-write, network on (npm install needs it)
Codex cannot express Jig's per-command allow/deny lists, so the boundary is coarser than with Claude Code:
inside a workspace-write sandbox the agent may run any command, confined to the workspace. Web search is
always off, so the `research` policy is refused (its validators need a web-evidence log).

Codex runs with --ignore-user-config and --ignore-rules (no personal settings or rules are inherited),
--ephemeral (no saved session) and --skip-git-repo-check. The answer is the agent's last message, which
must be the JSON object the command's schema describes; the runtime validates it as for any agent.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from .base import AgentRequest, AgentResponse

WRITE_TOOLS = {"Write", "Edit", "Bash"}


class CodexAdapter:
    name = "codex"

    def __init__(self, executable: str | None = None):
        self.executable = executable or shutil.which("codex")

    def available(self) -> tuple[bool, str]:
        if not self.executable:
            return False, "the `codex` CLI was not found on PATH"
        try:
            out = subprocess.run([self.executable, "--version"], capture_output=True, text=True, timeout=30)
            return out.returncode == 0, out.stdout.strip() or out.stderr.strip()
        except Exception as e:  # pragma: no cover - environment dependent
            return False, f"`codex --version` failed: {e}"

    def sandbox_mode(self, req: AgentRequest) -> str:
        return "workspace-write" if WRITE_TOOLS & set(req.policy.tools) else "read-only"

    def build_argv(self, req: AgentRequest, last_message: Path) -> list[str]:
        mode = self.sandbox_mode(req)
        argv = [self.executable, "exec", "--json", "--skip-git-repo-check", "--ephemeral",
                "--ignore-user-config", "--ignore-rules", "-C", str(req.cwd), "-s", mode,
                "-c", 'web_search="disabled"', "-o", str(last_message)]
        if mode == "workspace-write":
            argv += ["-c", "sandbox_workspace_write.network_access=true"]
        if sys.platform == "win32":
            # User config is ignored, so the Windows sandbox flavour is set here. "elevated" is the one under
            # which writes and commands work in a workspace-write session.
            argv += ["-c", 'windows.sandbox="elevated"']
        if req.model:
            argv += ["-m", req.model]
        if req.effort:
            argv += ["-c", f'model_reasoning_effort="{req.effort}"']
        return argv + ["-"]            # the prompt comes on stdin

    @staticmethod
    def full_prompt(req: AgentRequest) -> str:
        parts = [req.system.strip(), req.prompt.strip()]
        if req.output_schema is not None:
            schema = {k: v for k, v in req.output_schema.items() if k != "$schema"}
            parts.append("## Your final message\nWhen the work is done, your final message must be only one JSON "
                         "object (no prose, no code fence) that conforms to this JSON Schema:\n"
                         + json.dumps(schema, separators=(",", ":")))
        return "\n\n".join(p for p in parts if p)

    def invoke(self, req: AgentRequest) -> AgentResponse:
        ok, why = self.available()
        if not ok:
            return AgentResponse(ok=False, error_code="E_AGENT_UNAVAILABLE", error=why)
        if {"WebSearch", "WebFetch"} & set(req.policy.tools):
            return AgentResponse(ok=False, error_code="E_AGENT_UNAVAILABLE",
                                 error="the codex adapter does not support web research; use a claude_code agent")
        if req.sandbox is not None:
            return AgentResponse(ok=False, error_code="E_AGENT_UNAVAILABLE",
                                 error="the codex adapter does not run inside the Docker sandbox yet")
        req.cwd.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix="jig-codex-", suffix=".txt")
        os.close(fd)
        last = Path(tmp)
        argv = self.build_argv(req, last)
        started = time.monotonic()
        events_f = open(req.events_path, "a", encoding="utf-8") if req.events_path else None
        usage: dict = {}
        stderr_chunks: list[str] = []
        try:
            env = {**os.environ, **(req.env or {})}
            if self.sandbox_mode(req) == "workspace-write":
                env["npm_config_cache"] = str(req.cwd / ".npm-cache")   # the sandbox cannot write npm's default cache
            proc = subprocess.Popen(argv, cwd=str(req.cwd), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", env=env)
        except OSError as e:
            last.unlink(missing_ok=True)
            return AgentResponse(ok=False, error_code="E_AGENT_UNAVAILABLE", error=str(e))

        def feed():
            try:
                proc.stdin.write(self.full_prompt(req))
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
        errors: list[str] = []
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
                if ev.get("type") == "turn.completed" and isinstance(ev.get("usage"), dict):
                    for k, v in ev["usage"].items():
                        if isinstance(v, (int, float)):
                            usage[k] = usage.get(k, 0) + v
                elif ev.get("type") in ("error", "turn.failed"):
                    errors.append(json.dumps(ev)[:500])
                elif req.on_event:
                    s = _summarize(ev)
                    if s:
                        req.on_event(s)
            proc.wait()
        finally:
            timed_out = not timer.is_alive()
            timer.cancel()
            if events_f:
                events_f.close()
        elapsed = int((time.monotonic() - started) * 1000)
        text = last.read_text(encoding="utf-8", errors="replace") if last.exists() else ""
        last.unlink(missing_ok=True)
        token_usage = {"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
                       "cache_read_input_tokens": usage.get("cached_input_tokens")} if usage else None
        if token_usage:
            token_usage = {k: v for k, v in token_usage.items() if v is not None}
        if timed_out and proc.returncode not in (0, None):
            return AgentResponse(ok=False, error_code="E_TIMEOUT", duration_ms=elapsed, token_usage=token_usage,
                                 error=f"agent exceeded {req.timeout_s}s and was stopped")
        if proc.returncode != 0 or not text.strip():
            return AgentResponse(ok=False, error_code="E_AGENT_FAILED", duration_ms=elapsed, token_usage=token_usage,
                                 model=req.model, error=f"codex exited {proc.returncode}"
                                 + (f"; events: {' | '.join(errors)[-1500:]}" if errors else "")
                                 + f"; stderr: {''.join(stderr_chunks)[-1500:]}")
        return AgentResponse(ok=True, structured_output=parse_json_answer(text), text=text, model=req.model,
                             duration_ms=elapsed, token_usage=token_usage, cost_usd=None)


def parse_json_answer(text: str):
    """The last message should be a JSON object; tolerate a code fence or prose around it."""
    t = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", t, re.S)
    if m:
        t = m.group(1)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(t[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


def _summarize(ev: dict) -> str | None:
    item = ev.get("item") if isinstance(ev.get("item"), dict) else None
    if ev.get("type") != "item.completed" or not item:
        return None
    kind = item.get("type")
    if kind == "command_execution":
        return f"Bash {str(item.get('command', ''))[:120]}"
    if kind == "file_change":
        paths = [c.get("path", "") for c in item.get("changes", []) if isinstance(c, dict)]
        return f"Write {', '.join(paths)[:120]}"
    return None
