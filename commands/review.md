# Command: review ($artifact_id)

Review the code in your current directory (the artifact workspace). You have read-only tools; read the actual code before making any claim.

Criteria:
$criteria

Specification (for context):
<data name="spec">$spec</data>

- criteria_assessed: one entry per criterion above, using exactly those names; rating pass / concerns / fail.
- findings: RV-01, ...; each cites a real file path relative to the workspace and the line you saw it on, with a concrete recommendation.
- strengths: things done well, with specifics.
Report only issues you confirmed by reading the code.
