import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lattice import procedures  # noqa: E402
from lattice.adapters import FixtureAdapter  # noqa: E402
from lattice.config import DEFAULT_CONFIG, deep_merge, load_config, load_registry  # noqa: E402
from lattice.runtime import Runtime  # noqa: E402

from fixtures import Responder, write_junit_cmd  # noqa: E402


@pytest.fixture
def registry():
    reg = load_registry()
    # Replace the docker-based suites with portable commands that produce real JUnit XML.
    reg.stacks["java_react_postgres"]["test_suites"] = [
        {"name": "backend", "type": "junit", "command": write_junit_cmd("backend/target/surefire-reports/T.xml"),
         "reports": ["backend/target/surefire-reports/*.xml"], "clean": ["backend/target/surefire-reports"],
         "timeout_s": 60}]
    return reg


@pytest.fixture
def config():
    project_cfg = load_config(ROOT)  # real tool policies from lattice.yaml
    return deep_merge(DEFAULT_CONFIG, {"tool_policies": project_cfg["tool_policies"]})


@pytest.fixture
def make_rt(tmp_path, registry, config, monkeypatch):
    monkeypatch.setattr(procedures, "docker_available", lambda: (True, "stubbed"))

    def _make(overrides=None):
        responder = Responder(overrides)
        adapter = FixtureAdapter(responder)
        return Runtime(tmp_path, adapter=adapter, config=config, registry=registry), adapter

    return _make
