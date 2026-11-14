"""Agent adapter interface. The runtime only talks to agents through this."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class ToolPolicy:
    """Tool boundary enforced by the agent host (not by prompt text)."""
    name: str
    tools: list[str] = field(default_factory=list)      # tools that exist in the session at all
    allow: list[str] = field(default_factory=list)      # permission rules auto-approved
    deny: list[str] = field(default_factory=list)       # permission rules always denied


@dataclass
class AgentRequest:
    prompt: str
    system: str
    output_schema: dict | None
    policy: ToolPolicy
    cwd: Path
    model: str | None = None
    effort: str | None = None
    timeout_s: int = 1200
    max_budget_usd: float | None = None
    env: dict = field(default_factory=dict)  # extra environment (e.g. per-app ports), inherited by agent tools
    events_path: Path | None = None       # where to stream agent events (observability)
    on_event: Any = None                   # callback(summary: str)
    label: str = ""


@dataclass
class AgentResponse:
    ok: bool
    structured_output: Any = None
    text: str = ""
    model: str | None = None
    duration_ms: int | None = None
    token_usage: dict | None = None
    cost_usd: float | None = None
    num_turns: int | None = None
    permission_denials: list = field(default_factory=list)
    error_code: str | None = None
    error: str | None = None
    session_id: str | None = None


class AgentAdapter(Protocol):
    name: str

    def available(self) -> tuple[bool, str]:
        ...

    def invoke(self, req: AgentRequest) -> AgentResponse:
        ...
