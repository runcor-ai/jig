# Command: verify ($artifact_id, against=$against)

Verify the implementation in your current directory (the artifact workspace) against the items below. You have read-only tools. Read the code for every item.

Requirement artifact:
<data name="requirement">$requirement</data>

Design artifact:
<data name="design">$design</data>

Recorded test results (from the test runner, not from the build agent):
<data name="tests">$tests</data>

Items to verify (produce exactly one entry per id): $expected_ids

For each item:
- status: satisfied / partial / not_satisfied / unverifiable.
- evidence: file paths relative to the workspace, with `symbol` set to a class, method or identifier that literally appears in that file.
- test_evidence: names of test cases that exercise the item, copied exactly from the recorded test case names above. Leave empty if none.
- notes: what is missing for partial / not_satisfied.
A requirement is satisfied only if the code implements it end to end (API + persistence + UI where applicable) and server-side controls are enforced.
