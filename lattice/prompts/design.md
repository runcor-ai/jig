# Command: design ($artifact_id)

Requirement artifact:
<data name="requirement">$requirement</data>

Quality profile:
<data name="profile">$profile</data>

Stack profile and build contract (the build step and the test runner depend on this contract):
<data name="stack">$stack</data>
$decision_model_section
Caller notes:
<data name="notes">$notes</data>

Produce a design that a developer can implement directly.

- components: CMP-01, ...; name, responsibility, technology and the repository path that will hold it.
- data_model: every persisted entity with table name and fields (type and constraints). Include audit storage if the profile requires audit logging.
- api: every REST endpoint with method, path, roles allowed, and the FR ids it serves.
- security: authentication mechanism, server-side authorization model, roles and their permissions, audit approach, secrets handling.
- decisions: resolve EVERY open decision from the requirement (same D- ids): decision, rationale, alternatives, reversibility (high/medium/low). Prefer the simplest option that satisfies the requirements.
- traceability: one entry for EVERY functional requirement, naming component ids and endpoints ("METHOD /path").
- test_strategy: backend unit, backend integration (against PostgreSQL), frontend.
- repository_layout: top-level paths and their purpose; must include every `contract.required_paths` entry.
