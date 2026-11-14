"""Prove the hidden acceptance tests are correct before any candidate is scored with them.

Every brief has a reference implementation (jig_trust/reference/<ID>/logic.ts). This copies each one, with its
hidden tests placed exactly where the pack places them in a built app (src/__hidden__/<ID>.test.ts next to
src/logic.ts), and runs vitest. Every hidden test must pass on its reference, or the test is wrong.

    py experiments/trust/check_references.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE / "jig_trust"
WORK = HERE / "work" / "refcheck"

PACKAGE = {"name": "refcheck", "private": True, "type": "module",
           "devDependencies": {"vitest": "^3.2.4", "typescript": "^5.6.3"}}


def main() -> int:
    ids = sorted(p.stem.replace(".test", "") for p in (PACK / "hidden").glob("*.test.ts"))
    if WORK.exists():
        for d in WORK.iterdir():
            if d.name not in ("node_modules", "package.json", "package-lock.json"):
                shutil.rmtree(d) if d.is_dir() else d.unlink()
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "package.json").write_text(json.dumps(PACKAGE, indent=1), encoding="utf-8")
    npm = shutil.which("npm") or "npm"
    npx = shutil.which("npx") or "npx"
    if not (WORK / "node_modules" / "vitest").exists():
        subprocess.run([npm, "install", "--no-audit", "--no-fund"], cwd=WORK, check=True)
    for i in ids:
        src = WORK / i / "src"
        (src / "__hidden__").mkdir(parents=True)
        shutil.copy2(PACK / "reference" / i / "logic.ts", src / "logic.ts")
        shutil.copy2(PACK / "hidden" / f"{i}.test.ts", src / "__hidden__" / f"{i}.test.ts")
    report = WORK / "junit.xml"
    subprocess.run([npx, "vitest", "run", "--reporter=junit", f"--outputFile={report}"], cwd=WORK)
    cases = list(ET.parse(report).getroot().iter("testcase"))
    failed = [(c.get("classname"), c.get("name")) for c in cases if c.find("failure") is not None or c.find("error") is not None]
    per = {i: sum(1 for c in cases if (c.get("name") or "").startswith(f"{i} > H")) for i in ids}
    print(f"{len(cases)} hidden tests on {len(ids)} references; {len(failed)} failed")
    for i in ids:
        print(f"  {i:8} {per[i]} tests")
    for f in failed:
        print("  FAILED", f)
    ok = not failed and all(n == 6 for n in per.values())
    print("OK: every hidden test passes on its reference" if ok else "NOT OK")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
