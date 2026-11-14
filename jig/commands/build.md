# Command: build ($artifact_id)

You are working in the artifact workspace (your current directory). Implement the specification below as working software. Write every file inside the current directory. Do not create or modify a `.claude` directory.

Specification:
<data name="spec">$build_spec</data>

Caller notes:
<data name="notes">$notes</data>

Existing workspace state: $workspace_state

After you finish, Jig will run these commands itself, in this directory, and parse JUnit XML reports. They must succeed:
$test_run

Working method:
1. Create the project files directly with the Write tool (do not run interactive scaffolders). Include a README.md with setup, run and test instructions.
2. Write real automated tests for every must-have requirement.
3. Run the commands above yourself and fix failures until they pass.
4. Only Bash commands for npm/npx/node, curl against localhost and basic file listing are permitted; others are denied.

Report honestly: the commands you ran with their real outcome, the status of every requirement with evidence paths (relative to the workspace), and every known gap.
