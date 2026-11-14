"""Error codes. Every failure the runtime reports carries one of these."""
from __future__ import annotations

ERROR_CODES = {
    "E_PARSE": "Script could not be parsed or uses disallowed syntax",
    "E_UNKNOWN_COMMAND": "Command is not loaded (see `lattice commands`)",
    "E_COMMAND_DEF": "A command definition file is invalid",
    "E_PARAM": "Parameter missing, unknown, or of the wrong type",
    "E_UNKNOWN_ARTIFACT": "Referenced artifact does not exist",
    "E_ARTIFACT_EXISTS": "Script would create an artifact id that already exists (use --replace)",
    "E_MISSING_CONTEXT": "A stage this command requires has not completed",
    "E_AGENT_UNAVAILABLE": "The configured agent could not be started",
    "E_AGENT_FAILED": "The agent ran but did not return a usable result",
    "E_SCHEMA": "Agent output did not conform to the output schema",
    "E_VALIDATION": "Agent output failed semantic validation",
    "E_TIMEOUT": "Execution exceeded its time limit",
    "E_BUDGET": "Execution exceeded its cost budget",
    "E_PROCEDURE": "A runtime procedure (e.g. the test runner) failed",
    "E_UNAVAILABLE": "Capability or integration is not available in this environment",
}


class LatticeError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        assert code in ERROR_CODES, code
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, **({"details": self.details} if self.details else {})}
