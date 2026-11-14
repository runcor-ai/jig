import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lattice.adapters import FixtureAdapter  # noqa: E402
from lattice.config import DEFAULT_CONFIG  # noqa: E402
from lattice.loader import BUILTIN_DIR, load_commands  # noqa: E402
from lattice.runtime import Runtime  # noqa: E402

from fixtures import Responder  # noqa: E402


@pytest.fixture
def commands():
    # built-ins plus this repo's project commands (review), no user-level commands
    return load_commands(ROOT, dirs=[("builtin", BUILTIN_DIR), ("project", ROOT / "commands")])


@pytest.fixture
def make_rt(tmp_path, commands):
    def _make(overrides=None, sandbox=None):
        adapter = FixtureAdapter(Responder(overrides))
        rt = Runtime(tmp_path, adapter=adapter, config=DEFAULT_CONFIG, commands=commands, sandbox=sandbox)
        return rt, adapter
    return _make
