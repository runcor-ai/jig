"""`python fake_jig.py ...` behaves like `python -m jig ...` but uses the canned FixtureAdapter.
Used to test real multi-process batches without calling a model."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import jig.runtime as runtime_mod  # noqa: E402
from jig.adapters import FixtureAdapter  # noqa: E402
from jig.cli import main  # noqa: E402
from jig.loader import BUILTIN_DIR, load_commands  # noqa: E402

from fixtures import Responder  # noqa: E402

_orig_init = runtime_mod.Runtime.__init__


def _init(self, project_dir, adapter=None, **kw):
    kw["commands"] = load_commands(ROOT, dirs=[("builtin", BUILTIN_DIR), ("project", ROOT / "commands")])
    _orig_init(self, project_dir, adapter=FixtureAdapter(Responder()), **kw)


runtime_mod.Runtime.__init__ = _init

if __name__ == "__main__":
    sys.exit(main())
