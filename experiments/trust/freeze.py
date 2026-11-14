"""Write jig_trust/frozen.py: the sha256 of every brief, hidden test, reference and the trial pipeline.

The engine's lock fingerprints only .py files. frozen.py is a .py file, so the lock covers these hashes, and the
pack refuses to start if any frozen file has changed since.

    py experiments/trust/freeze.py
"""
import hashlib
from pathlib import Path

PACK = Path(__file__).resolve().parent / "jig_trust"


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


files = sorted(p for p in PACK.rglob("*") if p.is_file() and p.suffix in (".md", ".ts", ".jig")
               and "__pycache__" not in p.parts)
lines = ['"""Frozen before the first run: sha256 of every non-code file of the pack (see freeze.py)."""', "FROZEN = {"]
lines += [f'    "{p.relative_to(PACK).as_posix()}": "{digest(p)}",' for p in files]
lines += ["}", ""]
(PACK / "frozen.py").write_text("\n".join(lines), encoding="utf-8")
print(f"froze {len(files)} files")
