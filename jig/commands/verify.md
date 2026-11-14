# Command: verify ($artifact_id)

Verify the implementation in your current directory (the artifact workspace) against the specification. You have read-only tools. Read the code for every item.

Specification:
<data name="spec">$spec</data>

Recorded test results (from Jig's own test run, not from the build agent):
<data name="tests">$tests</data>

Items to verify (produce exactly one entry per id): $expected_ids

For each item:
- status: satisfied / partial / not_satisfied / unverifiable.
- evidence: file paths relative to the workspace, with `symbol` set to a class, function or identifier that literally appears in that file.
- test_evidence: names of test cases that exercise the item, copied exactly from the recorded test case names above. Leave empty if none.
- notes: what is missing for partial / not_satisfied.
