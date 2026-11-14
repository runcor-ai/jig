"""`python fake_lattice.py ...` behaves like `python -m lattice ...` but uses the canned FixtureAdapter
and portable test suites. Used to test real multi-process batches without calling Claude."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import lattice.runtime as runtime_mod  # noqa: E402
from lattice import procedures  # noqa: E402
from lattice.adapters import FixtureAdapter  # noqa: E402
from lattice.cli import main  # noqa: E402
from lattice.config import load_registry  # noqa: E402

from fixtures import Responder, write_junit_cmd  # noqa: E402

_orig_init = runtime_mod.Runtime.__init__


def _init(self, project_dir, adapter=None, **kw):
    reg = load_registry()
    for st in reg.stacks.values():
        st["test_suites"] = [{"name": "unit", "type": "junit",
                              "command": write_junit_cmd("test-results/junit.xml"),
                              "reports": ["test-results/*.xml"], "clean": ["test-results"], "timeout_s": 60}]
    _orig_init(self, project_dir, adapter=FixtureAdapter(Responder()), registry=reg, **kw)


runtime_mod.Runtime.__init__ = _init
procedures.docker_available = lambda: (True, "stubbed")

if __name__ == "__main__":
    sys.exit(main())
