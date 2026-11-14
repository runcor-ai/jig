# Command: build ($artifact_id)

You are working in the artifact workspace (your current directory). Implement the design below as a working application. Write every file inside the current directory. Do not create or modify a `.claude` directory.

Requirement artifact:
<data name="requirement">$requirement</data>

Design artifact:
<data name="design">$design</data>

Quality profile:
<data name="profile">$profile</data>

Stack profile:
<data name="stack">$stack</data>

Build contract (an automated test runner will execute exactly these, so they must work):
$contract_rules

Caller notes:
<data name="notes">$notes</data>

Existing workspace state: $workspace_state

Working method:
$build_steps
- Only Bash commands for docker, npm/npx/node, curl against localhost and basic file inspection are permitted; other commands will be denied. Prefer the dedicated Write/Edit/Read/Glob/Grep tools for files.

Report honestly: list the commands you ran with their real outcome, the status of every functional requirement with evidence paths (relative to the workspace), and every known gap.
