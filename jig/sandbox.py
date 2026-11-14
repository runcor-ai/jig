"""--sandbox docker: run the agent (and test commands) inside a throwaway container.

Only the artifact workspace is mounted (at /workspace). The host filesystem, the
user's ~/.claude settings and other projects are not visible. This is the real
isolation boundary; the Claude Code permission flags still apply inside it.

Authentication: the container cannot use the host's interactive login. Create a
long-lived token once with `claude setup-token` and export it as
CLAUDE_CODE_OAUTH_TOKEN (or use ANTHROPIC_API_KEY). It is passed into the container
by *name* (`-e NAME`), so its value never appears on a command line. Note that the
agent inside the container can read it; use a token you can revoke.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

IMAGE = "jig-agent:0.1"
# The root filesystem is read-only. Only these are writable (plus the /workspace bind mount):
#   /tmp        scratch space for npm, vitest, etc.
#   /home/node  HOME: npm cache (~/.npm, including npx binaries, hence `exec`) and Claude Code's own
#               config (~/.claude/, ~/.claude.json), which it writes at startup.
# Both are memory-backed and discarded when the container exits.
TMPFS = ["/tmp:rw,exec,nosuid,size=1g,mode=1777",
         "/home/node:rw,exec,nosuid,size=2g,uid=1000,gid=1000,mode=0755"]
DOCKERFILE_DIR = Path(__file__).resolve().parent.parent / "docker"
TOKEN_VARS = ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY")


class DockerSandbox:
    name = "docker"

    def __init__(self, image: str = IMAGE, memory: str = "4g", cpus: str = "2"):
        self.image = image
        self.memory = memory
        self.cpus = cpus
        self.docker = shutil.which("docker")

    def token_var(self) -> str | None:
        return next((v for v in TOKEN_VARS if os.environ.get(v)), None)

    def check(self) -> tuple[bool, str]:
        """(ok, explanation). Every reason it cannot run is reported explicitly."""
        if not self.docker:
            return False, "docker CLI not found on PATH"
        p = subprocess.run([self.docker, "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True)
        if p.returncode != 0:
            return False, "docker daemon is not running"
        p = subprocess.run([self.docker, "image", "inspect", self.image], capture_output=True, text=True)
        if p.returncode != 0:
            return False, f"image {self.image} not built: run `jig sandbox-build`"
        if not self.token_var():
            return False, ("no credentials for the container: run `claude setup-token` and set "
                           "CLAUDE_CODE_OAUTH_TOKEN (or ANTHROPIC_API_KEY)")
        return True, f"docker {self.image}, credentials from ${self.token_var()}"

    def wrap(self, argv: list[str], workspace: Path, env: dict | None = None) -> list[str]:
        ws = str(Path(workspace).resolve())
        out = [self.docker or "docker", "run", "--rm", "-i",
               "-v", f"{ws}:/workspace", "-w", "/workspace",
               "--read-only", *[a for t in TMPFS for a in ("--tmpfs", t)],
               "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
               "--pids-limit", "512", "--memory", self.memory, "--cpus", self.cpus]
        tv = self.token_var()
        if tv:
            out += ["-e", tv]                      # value inherited from our environment, not on argv
        for k, v in (env or {}).items():
            out += ["-e", f"{k}={v}"]
        return out + [self.image, *argv]


def build_image(image: str = IMAGE) -> int:
    docker = shutil.which("docker") or "docker"
    return subprocess.call([docker, "build", "-t", image, str(DOCKERFILE_DIR)])


SANDBOXES = {"docker": DockerSandbox}


def make_sandbox(name: str | None):
    if not name or name == "none":
        return None
    if name not in SANDBOXES:
        raise ValueError(f"unknown sandbox '{name}'; available: none, {', '.join(SANDBOXES)}")
    return SANDBOXES[name]()
