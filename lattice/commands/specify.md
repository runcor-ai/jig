# Command: specify

Goal:
<data name="target">$target</data>

Constraints from the caller:
<data name="constraints">$constraints</data>

Additional brief:
<data name="brief">$brief</data>

Write a specification a developer can implement directly, sized to the goal (do not inflate a small goal).

- requirements: R-01, R-02, ...; each with priority (must/should/could) and concrete, testable acceptance statements.
- constraints_applied: restate every caller constraint and how the spec honours it.
- assumptions: business rules or details you had to assume.
- decisions: choices you made (question, decision, rationale).
- components: the parts to build, each with its responsibility and the path it will live at.
- test_plan: what automated tests will prove the must-have requirements.
- out_of_scope: what you deliberately left out.
- artifact_code: 2-6 uppercase letters naming the thing (used for its id).
