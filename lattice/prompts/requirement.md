# Command: requirement

Goal:
<data name="target">$target</data>

Resolved quality profile:
<data name="profile">$profile</data>

Resolved stack profile:
<data name="stack">$stack</data>

Additional brief supplied by the caller:
<data name="brief">$brief</data>

Produce the requirement set for this goal.

- functional_requirements: FR-01, FR-02, ... Each has priority (must/should/could) and concrete, testable acceptance statements. Cover what a competent business analyst would expect for this goal and anything in the brief; do not invent exotic features.
- non_functional_requirements: include one NFR for EVERY enabled profile control, with `source` set exactly to `profile:<dotted.path>`. Enabled controls: $controls. Additional NFRs use source `inferred`.
- constraints: one constraint per stack component, naming it exactly ($stack_terms), with source `stack:$stack_name`.
- assumptions: business rules you had to assume. Set needs_confirmation=true where a wrong assumption would materially change the design.
- open_decisions: unspecified business rules or choices that the design step must resolve (D-01, ...), each with options and a recommendation.
- acceptance_criteria: AC-01, ...; each lists the FR ids it verifies. Every `must` requirement is verified by at least one criterion.
- artifact_code: 2-6 uppercase letters naming the system (use the conventional domain acronym).
