# Command: review ($artifact_id)

Review the code in your current directory (the artifact workspace) against these criteria: $criteria.
You have read-only tools. Read the actual code before making any claim.

Requirement artifact (for context):
<data name="requirement">$requirement</data>

Design artifact (for context):
<data name="design">$design</data>

- criteria_assessed: one entry per criterion, using exactly these names: $criteria. Rating pass / concerns / fail.
- findings: RV-01, ...; each cites a real file path relative to the workspace and, where applicable, the line number you saw it on. Severity reflects real-world impact. Give a concrete recommendation.
- strengths: things done well, with specifics.
Report only issues you confirmed by reading the code.
