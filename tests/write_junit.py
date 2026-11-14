"""Test helper standing in for a real test runner: writes a JUnit report.
usage: python write_junit.py <report path> [pass|fail|none]"""
import sys
from pathlib import Path

PASS = """<?xml version="1.0"?>
<testsuite name="pong" tests="2" failures="0">
  <testcase classname="src/logic.test.ts" name="ball bounces off walls" time="0.01"/>
  <testcase classname="src/logic.test.ts" name="scores to ten" time="0.01"/>
</testsuite>"""
FAIL = """<?xml version="1.0"?>
<testsuite name="pong" tests="1" failures="1">
  <testcase classname="src/logic.test.ts" name="scores to ten"><failure message="expected 10, got 9"/></testcase>
</testsuite>"""

mode = sys.argv[2] if len(sys.argv) > 2 else "pass"
if mode != "none":
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(PASS if mode == "pass" else FAIL)
sys.exit(0 if mode != "fail" else 1)
