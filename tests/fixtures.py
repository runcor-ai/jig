"""Canned agent outputs and a responder for FixtureAdapter-based tests (no model calls)."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from jig.adapters import AgentResponse

HERE = Path(__file__).resolve().parent
PY = Path(sys.executable).as_posix()
HELPER = (HERE / "write_junit.py").as_posix()


def junit_cmd(mode: str = "pass", report: str = "test-results/junit.xml") -> str:
    """A test command string (as a script would write it) that produces a real JUnit report."""
    return f'"{PY}" "{HELPER}" {report} {mode}'


SPEC = {
    "title": "Pong", "artifact_code": "PONG", "summary": "Browser pong",
    "requirements": [
        {"id": "R-01", "title": "Ball bounces", "description": "d", "priority": "must", "acceptance": ["a"]},
        {"id": "R-02", "title": "Score to ten", "description": "d", "priority": "must", "acceptance": ["a"]},
        {"id": "R-03", "title": "Sound", "description": "d", "priority": "could", "acceptance": ["a"]},
    ],
    "constraints_applied": [{"constraint": "React + TypeScript", "how": "Vite app"}],
    "assumptions": ["keyboard only"], "decisions": [{"question": "q", "decision": "d", "rationale": "r"}],
    "components": [{"name": "Game", "responsibility": "loop", "path": "src/game.ts"}],
    "test_plan": "vitest", "out_of_scope": ["online play"],
}

BUILD_FILES = {
    "package.json": "{}",
    "src/game.ts": "export function step() {}\nexport function score() {}\n",
    "README.md": "# Pong\n",
}

BUILD = {
    "summary": "built", "files_created": list(BUILD_FILES),
    "requirements_implemented": [{"requirement": "R-01", "status": "implemented", "evidence_paths": ["src/game.ts"],
                                  "notes": ""}],
    "commands_run": [{"command": "npm test", "outcome": "passed"}], "known_gaps": [],
    "run_instructions": "npm run dev",
}

VERIFY = {
    "summary": "verified",
    "items": [
        {"id": "R-01", "status": "satisfied",
         "evidence": [{"file": "src/game.ts", "symbol": "step", "note": "loop"}],
         "test_evidence": ["src/logic.test.ts.ball bounces off walls"], "notes": ""},
        {"id": "R-02", "status": "satisfied", "evidence": [{"file": "/workspace/src/game.ts", "symbol": "score",
                                                             "note": "sandbox-style absolute path"}],
         "test_evidence": [], "notes": ""},
        {"id": "R-03", "status": "not_satisfied", "evidence": [], "test_evidence": [], "notes": "no sound"},
    ],
}

REVIEW = {
    "summary": "ok",
    "criteria_assessed": [{"criterion": "correctness", "rating": "pass", "summary": "s"},
                          {"criterion": "readability", "rating": "concerns", "summary": "s"}],
    "findings": [{"id": "RV-01", "criterion": "readability", "severity": "low", "title": "t", "description": "d",
                  "file": "src/game.ts", "line": 2, "recommendation": "r"}],
    "strengths": ["small"],
}

RESEARCH = {
    "summary": "Passkeys are growing.",
    "findings": [{"id": "F-01", "claim": "Platforms support passkeys", "confidence": "high", "source_ids": ["S-01"]},
                 {"id": "F-02", "claim": "Adoption is uneven", "confidence": "medium", "source_ids": ["S-02", "S-03"]}],
    "sources": [{"id": "S-01", "url": "https://example.org/passkeys", "title": "A", "excerpt": "e"},
                {"id": "S-02", "url": "https://www.example.com/report-2026/", "title": "B", "excerpt": "e"},
                {"id": "S-03", "url": "https://news.example.net/item?id=7", "title": "C", "excerpt": "e"}],
    "open_questions": [], "method": "searched",
}
# What the agent's own WebSearch/WebFetch calls returned in the session (the evidence log).
RESEARCH_EVENTS = [
    {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "WebFetch",
                                                   "input": {"url": "https://example.org/passkeys"}}]}},
    {"type": "user", "message": {"content": [{"type": "tool_result", "content":
        "Results: https://example.com/report-2026 ... https:\\/\\/news.example.net\\/item?id=7"}]}},
]


class Responder:
    """Returns canned outputs per command; a list value is a sequence (for retries)."""

    def __init__(self, overrides: dict | None = None):
        self.outputs = {"specify": SPEC, "build": BUILD, "verify": VERIFY, "review": REVIEW, "research": RESEARCH}
        self.sequences: dict[str, list] = {}
        for k, v in (overrides or {}).items():
            if isinstance(v, list):
                self.sequences[k] = list(v)
            else:
                self.outputs[k] = v

    def __call__(self, req):
        cmd = req.system.split("`")[1]  # the system prompt names the command in backticks
        if req.events_path and cmd == "research":
            with open(req.events_path, "a", encoding="utf-8") as f:
                for ev in RESEARCH_EVENTS:
                    f.write(json.dumps(ev) + "\n")
        if cmd == "build":
            for rel, text in BUILD_FILES.items():
                p = Path(req.cwd) / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text)
        out = self.sequences[cmd].pop(0) if self.sequences.get(cmd) else self.outputs.get(cmd)
        if isinstance(out, AgentResponse):
            return out
        return AgentResponse(ok=True, structured_output=copy.deepcopy(out), model="fixture", duration_ms=5,
                             token_usage={"input_tokens": 10, "output_tokens": 20}, cost_usd=0.001)
