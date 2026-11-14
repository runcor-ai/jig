"""Deterministic offline adapter for tests. Never the default; results are labelled model='fixture'."""
from __future__ import annotations

from typing import Callable

from .base import AgentRequest, AgentResponse


class FixtureAdapter:
    name = "fixture"

    def __init__(self, responder: Callable[[AgentRequest], object]):
        self.responder = responder
        self.requests: list[AgentRequest] = []

    def available(self) -> tuple[bool, str]:
        return True, "fixture"

    def invoke(self, req: AgentRequest) -> AgentResponse:
        self.requests.append(req)
        out = self.responder(req)
        if isinstance(out, AgentResponse):
            return out
        return AgentResponse(ok=True, structured_output=out, model="fixture")
