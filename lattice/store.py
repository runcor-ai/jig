"""Filesystem persistence for artifacts, runs and approvals.

Layout (under the configured store dir, default .lattice/):
    artifacts/<ID>/manifest.json                 current state of the artifact
    artifacts/<ID>/stages/<stage>/<run_id>.json   every stage output ever produced (append-only)
    artifacts/<ID>/checkpoints/<label>/           checkpoint snapshots
    runs/<run_id>/{invocation,result,status}.json, prompt.md, agent_events.jsonl
    log.jsonl                                    one line per execution
    approvals.json                               human approvals
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import socket
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ID_RE = re.compile(r"^[A-Z][A-Z0-9]{1,7}-\d{3}$")
PORT_BASE, PORT_STRIDE, PORT_SLOTS = 20000, 10, 400
PORT_KEYS = ("backend", "frontend", "db")


class LockTimeout(RuntimeError):
    pass


@contextlib.contextmanager
def file_lock(path: Path, timeout_s: float = 60.0, stale_s: float = 120.0):
    """Cross-process lock using an exclusively-created lock file (works on Windows and POSIX)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > stale_s:  # holder died
                    path.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() > deadline:
                raise LockTimeout(f"could not acquire {path}") from None
            time.sleep(0.02)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    os.replace(tmp, path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


class Store:
    def __init__(self, root: Path):
        self.root = root
        (root / "artifacts").mkdir(parents=True, exist_ok=True)
        (root / "runs").mkdir(parents=True, exist_ok=True)

    # ── artifacts ──────────────────────────────────────────────────────
    def artifact_dir(self, aid: str) -> Path:
        if not ID_RE.match(aid):
            raise ValueError(f"invalid artifact id '{aid}'")
        return self.root / "artifacts" / aid

    def exists(self, aid: str) -> bool:
        return ID_RE.match(aid or "") is not None and (self.artifact_dir(aid) / "manifest.json").exists()

    def list_ids(self) -> list[str]:
        return sorted(p.name for p in (self.root / "artifacts").iterdir() if (p / "manifest.json").exists())

    def lock(self, name: str):
        return file_lock(self.root / "locks" / f"{name}.lock")

    def next_id(self, code: str) -> str:
        n = 0
        for p in (self.root / "artifacts").iterdir():
            c, _, num = p.name.rpartition("-")
            if c == code and num.isdigit():
                n = max(n, int(num))
        return f"{code}-{n + 1:03d}"

    def create_artifact(self, aid: str | None, title: str, meta: dict, code: str = "ART") -> dict:
        """Atomically claim an id (exclusive mkdir) so parallel scripts never share one.

        With aid=None the next free <code>-NNN is claimed.
        """
        with self.lock("ids"):
            if aid is None:
                aid = self.next_id(code)
            d = self.artifact_dir(aid)
            try:
                d.mkdir(parents=True, exist_ok=False)
            except FileExistsError:
                raise FileExistsError(f"artifact {aid} already exists") from None
            manifest = {"id": aid, "title": title, "created_at": now_iso(), "updated_at": now_iso(),
                        "stages": {}, "history": [], **meta}
            manifest["ports"] = self._allocate_ports(aid)
            write_json(d / "manifest.json", manifest)
        return manifest

    def _allocate_ports(self, aid: str) -> dict:
        """Give each artifact its own host ports so parallel apps never collide. Caller holds the ids lock."""
        used = set()
        for other in self.list_ids():
            if other == aid:
                continue
            used |= set((self.manifest(other).get("ports") or {}).values())
        for slot in range(PORT_SLOTS):
            base = PORT_BASE + slot * PORT_STRIDE
            ports = {k: base + i for i, k in enumerate(PORT_KEYS)}
            if not (set(ports.values()) & used) and all(_port_free(p) for p in ports.values()):
                return ports
        raise RuntimeError("no free port block available")

    def archive_artifact(self, aid: str) -> Path:
        """Move an artifact aside (non-destructive) so its id can be reused."""
        dest = self.root / "archive" / f"{aid}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(self.artifact_dir(aid)), dest)
        return dest

    def manifest(self, aid: str) -> dict:
        m = read_json(self.artifact_dir(aid) / "manifest.json")
        if m is None:
            raise KeyError(aid)
        return m

    def save_manifest(self, m: dict) -> None:
        m["updated_at"] = now_iso()
        write_json(self.artifact_dir(m["id"]) / "manifest.json", m)

    def record_stage(self, aid: str, stage: str, run_id: str, status: str, output: Any, validation: dict,
                     cost_usd: float | None = None) -> Path:
        path = self.artifact_dir(aid) / "stages" / stage / f"{run_id}.json"
        write_json(path, {"stage": stage, "run_id": run_id, "status": status, "recorded_at": now_iso(),
                          "validation": validation, "output": output})
        with self.lock(f"artifact-{aid}"):
            m = self.manifest(aid)
            m["stages"][stage] = {"status": status, "run_id": run_id, "file": str(path.relative_to(self.root)),
                                  "validation_passed": validation.get("passed"), "updated_at": now_iso(),
                                  "params": validation.get("params"), "cost_usd": cost_usd}
            m["history"].append({"stage": stage, "run_id": run_id, "status": status, "at": now_iso()})
            m["cost_usd"] = round((m.get("cost_usd") or 0) + (cost_usd or 0), 6)
            self.save_manifest(m)
        return path

    def update_manifest(self, aid: str, **fields) -> dict:
        with self.lock(f"artifact-{aid}"):
            m = self.manifest(aid)
            m.update(fields)
            self.save_manifest(m)
        return m

    def stage_output(self, aid: str, stage: str) -> Any:
        m = self.manifest(aid)
        st = m["stages"].get(stage)
        if not st:
            return None
        return read_json(self.root / st["file"])["output"]

    # ── runs ───────────────────────────────────────────────────────────
    def new_run(self, command: str) -> tuple[str, Path]:
        rid = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{command}-{uuid.uuid4().hex[:6]}"
        d = self.root / "runs" / rid
        d.mkdir(parents=True)
        return rid, d

    def set_run_status(self, run_dir: Path, **fields) -> None:
        st = read_json(run_dir / "status.json", {}) or {}
        st.update(fields, updated_at=now_iso())
        write_json(run_dir / "status.json", st)

    def append_log(self, entry: dict) -> None:
        with self.lock("log"), open(self.root / "log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"at": now_iso(), **entry}, default=str) + "\n")

    def running(self) -> list[dict]:
        out = []
        for d in sorted((self.root / "runs").iterdir()):
            st = read_json(d / "status.json")
            if st and st.get("state") == "running":
                out.append({"run_id": d.name, **st})
        return out

    # ── approvals ──────────────────────────────────────────────────────
    def approvals(self) -> list[dict]:
        return read_json(self.root / "approvals.json", []) or []

    def add_approval(self, entry: dict) -> None:
        with self.lock("approvals"):
            a = self.approvals()
            a.append({**entry, "at": now_iso()})
            write_json(self.root / "approvals.json", a)

    def consume_approval(self, aid: str, command: str) -> dict | None:
        """Approvals are single-use: consumed by the command they authorize."""
        with self.lock("approvals"):
            a = self.approvals()
            for e in a:
                if e.get("artifact_id") == aid and e.get("command") == command and not e.get("consumed_at"):
                    e["consumed_at"] = now_iso()
                    write_json(self.root / "approvals.json", a)
                    return e
        return None
