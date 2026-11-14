"""Canned agent outputs and a responder for FixtureAdapter-based tests."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

from lattice.adapters import AgentResponse

CONTROLS = ["security.authentication_required", "security.authorization_required", "security.audit_logging",
            "security.secrets_management", "security.input_validation", "quality.automated_tests",
            "quality.code_review", "quality.documentation", "deployment.production_approval_required"]

REQUIREMENT = {
    "title": "Customer management", "artifact_code": "CRM", "summary": "CRM app",
    "functional_requirements": [
        {"id": "FR-01", "title": "Create customer", "description": "d", "priority": "must", "acceptance": ["a"]},
        {"id": "FR-02", "title": "Search customers", "description": "d", "priority": "must", "acceptance": ["a"]},
    ],
    "non_functional_requirements": [
        {"id": f"NFR-{i + 1:02d}", "category": c.split(".")[0], "description": c, "source": f"profile:{c}"}
        for i, c in enumerate(CONTROLS)],
    "constraints": [{"id": f"C-{i + 1:02d}", "description": f"Use {t}", "source": "stack:java_react_postgres"}
                    for i, t in enumerate(["Java", "Spring Boot", "React", "TypeScript", "PostgreSQL"])],
    "assumptions": [{"id": "A-01", "description": "Single tenant", "needs_confirmation": True}],
    "open_decisions": [{"id": "D-01", "question": "Auth mechanism?", "options": ["JWT", "session"],
                        "recommended": "JWT", "impact": "security"}],
    "acceptance_criteria": [{"id": "AC-01", "description": "CRUD works", "verifies": ["FR-01", "FR-02"]}],
    "out_of_scope": ["billing"],
}

DESIGN = {
    "overview": "Layered app", "architecture_style": "modular monolith",
    "components": [{"id": "CMP-01", "name": "API", "responsibility": "REST", "technology": "Spring Boot",
                    "path": "backend/"},
                   {"id": "CMP-02", "name": "UI", "responsibility": "SPA", "technology": "React", "path": "frontend/"}],
    "data_model": [{"entity": "Customer", "table": "customers",
                    "fields": [{"name": "id", "type": "uuid", "constraints": "pk"}], "notes": ""}],
    "api": [{"method": "POST", "path": "/api/customers", "description": "create", "roles": ["AGENT"],
             "requirements": ["FR-01"]},
            {"method": "GET", "path": "/api/customers", "description": "search", "roles": ["AGENT"],
             "requirements": ["FR-02"]}],
    "security": {"authentication": "JWT", "authorization": "RBAC", "roles": [{"name": "AGENT", "permissions": ["x"]}],
                 "audit": "audit table", "secrets": "env"},
    "decisions": [{"id": "D-01", "question": "Auth?", "decision": "JWT", "rationale": "simple",
                   "alternatives": ["session"], "reversibility": "medium"}],
    "traceability": [{"requirement": "FR-01", "components": ["CMP-01"], "endpoints": ["POST /api/customers"],
                      "notes": ""},
                     {"requirement": "FR-02", "components": ["CMP-01", "CMP-02"], "endpoints": ["GET /api/customers"],
                      "notes": ""}],
    "test_strategy": {"backend_unit": "JUnit", "backend_integration": "Testcontainers", "frontend": "Vitest"},
    "repository_layout": [{"path": "backend/pom.xml", "purpose": "build"}, {"path": "frontend/", "purpose": "ui"},
                          {"path": "docker-compose.yml", "purpose": "dev"}, {"path": "README.md", "purpose": "docs"}],
}

BUILD_FILES = {
    "backend/pom.xml": "<project/>",
    "backend/src/main/java/crm/CustomerController.java":
        "package crm;\npublic class CustomerController {\n  public void create() {}\n  public void search() {}\n}\n",
    "backend/src/main/resources/db/migration/V1__init.sql": "create table customers(id uuid primary key);\n",
    "frontend/package.json": "{}",
    "README.md": "# CRM\n",
    "docker-compose.yml": "services:\n  db: {}\n  backend: {}\n  frontend: {}\n  backend-test: {}\n  frontend-test: {}\n",
}

BUILD = {
    "summary": "built", "files_created": list(BUILD_FILES),
    "requirements_implemented": [
        {"requirement": "FR-01", "status": "implemented",
         "evidence_paths": ["backend/src/main/java/crm/CustomerController.java"], "notes": ""},
        {"requirement": "FR-02", "status": "implemented",
         "evidence_paths": ["backend/src/main/java/crm/CustomerController.java"], "notes": ""}],
    "commands_run": [{"command": "docker compose run --rm backend-test", "outcome": "passed"}],
    "known_gaps": [], "run_instructions": "docker compose up",
}

REVIEW = {
    "summary": "ok",
    "criteria_assessed": [{"criterion": "security", "rating": "concerns", "summary": "s"},
                          {"criterion": "architecture", "rating": "pass", "summary": "a"}],
    "findings": [{"id": "RV-01", "criterion": "security", "severity": "medium", "title": "t", "description": "d",
                  "file": "backend/src/main/java/crm/CustomerController.java", "line": 2, "recommendation": "r"}],
    "strengths": ["clear"],
}

VERIFY = {
    "summary": "verified",
    "items": [
        {"id": "FR-01", "status": "satisfied",
         "evidence": [{"file": "backend/src/main/java/crm/CustomerController.java",
                       "symbol": "CustomerController.create", "note": "endpoint"}],
         "test_evidence": ["crm.CustomerIT.createsCustomer"], "notes": ""},
        {"id": "FR-02", "status": "satisfied",
         "evidence": [{"file": "backend/src/main/java/crm/CustomerController.java",
                       "symbol": "CustomerController.search", "note": "endpoint"}],
         "test_evidence": [], "notes": ""},
        {"id": "AC-01", "status": "satisfied",
         "evidence": [{"file": "backend/src/main/java/crm/CustomerController.java", "symbol": "", "note": "n"}],
         "test_evidence": [], "notes": ""},
    ],
}

JUNIT_PASS = """<?xml version="1.0"?>
<testsuite name="crm.CustomerIT" tests="2" failures="0">
  <testcase classname="crm.CustomerIT" name="createsCustomer" time="0.1"/>
  <testcase classname="crm.CustomerIT" name="searchesCustomers" time="0.1"/>
</testsuite>"""


def write_junit_cmd(rel: str, content: str = JUNIT_PASS) -> list[str]:
    """A portable command that writes a JUnit report (stands in for `docker compose run backend-test`)."""
    code = (f"import pathlib; p=pathlib.Path({rel!r}); p.parent.mkdir(parents=True, exist_ok=True); "
            f"p.write_text({content!r})")
    return [sys.executable, "-c", code]


RESEARCH = {
    "summary": "Passkeys are growing.",
    "findings": [{"id": "F-01", "claim": "Major platforms support passkeys", "confidence": "high",
                  "source_ids": ["S-01"]},
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
    """Returns canned outputs per command; optionally a sequence of outputs to exercise retries."""

    def __init__(self, overrides: dict | None = None):
        self.outputs = {"requirement": REQUIREMENT, "design": DESIGN, "build": BUILD, "review": REVIEW,
                        "verify": VERIFY, "research": RESEARCH}
        self.events = {"research": RESEARCH_EVENTS}
        self.sequences: dict[str, list] = {}
        for k, v in (overrides or {}).items():
            if isinstance(v, list):
                self.sequences[k] = list(v)
            else:
                self.outputs[k] = v

    def __call__(self, req):
        cmd = req.system.split("`")[1]  # system prompt names the command in backticks
        if req.events_path and cmd in self.events:
            import json
            with open(req.events_path, "a", encoding="utf-8") as f:
                for ev in self.events[cmd]:
                    f.write(json.dumps(ev) + "\n")
        if cmd == "build":
            for rel, text in BUILD_FILES.items():
                p = Path(req.cwd) / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text)
        if cmd in self.sequences and self.sequences[cmd]:
            out = self.sequences[cmd].pop(0)
        else:
            out = self.outputs.get(cmd, {"summary": "generic", "items": [], "findings": [], "assumptions": [],
                                         "recommendations": [], "confidence": "medium"})
        if isinstance(out, AgentResponse):
            return out
        return AgentResponse(ok=True, structured_output=copy.deepcopy(out), model="fixture", duration_ms=5,
                             token_usage={"input_tokens": 10, "output_tokens": 20}, cost_usd=0.001)
