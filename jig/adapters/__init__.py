from .base import AgentAdapter, AgentRequest, AgentResponse, ToolPolicy
from .claude_code import ClaudeCodeAdapter
from .fixture import FixtureAdapter

ADAPTERS = {"claude_code": ClaudeCodeAdapter}


def make_adapter(name: str):
    if name not in ADAPTERS:
        raise ValueError(f"unknown agent adapter '{name}'. Available: {', '.join(ADAPTERS)}")
    return ADAPTERS[name]()


__all__ = ["AgentAdapter", "AgentRequest", "AgentResponse", "ToolPolicy", "ClaudeCodeAdapter", "FixtureAdapter",
           "make_adapter"]
