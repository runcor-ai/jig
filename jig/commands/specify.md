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

Spec format: $format

If the spec format is `facts`, also fill `facts`: the whole specification written as notes under five headings,
`## THINGS`, `## VALUES`, `## RULES`, `## LINKS` and `## TIMING`, each a list of one-line facts. Write every fact as
one short bullet in key-value form: 'name: value' (for example 'R-02.win_score: 10') or 'a -> b: relation' (for
example 'ball -> paddle: bounces off'). One fact per bullet, no prose, no repetition. Put each fact under the section
it belongs to. Every requirement must appear, by its id, as one or more facts (usually under RULES), with every
number and acceptance condition it needs, so that a developer can build from these notes alone. If the format is
`prose`, leave `facts` out.
