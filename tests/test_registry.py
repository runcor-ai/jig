from collections import Counter

import jsonschema
import pytest

from lattice.config import SCHEMA_DIR, load_registry
from lattice.profiles import ProfileError, enabled_controls, resolve_profile, resolve_stack


def test_registry_has_32_commands_4_per_category():
    reg = load_registry()
    assert len(reg.commands) == 32
    assert set(Counter(s["category"] for s in reg.commands.values()).values()) == {4}


def test_every_schema_is_valid_json_schema():
    for f in SCHEMA_DIR.glob("*.json"):
        import json
        jsonschema.Draft202012Validator.check_schema(json.loads(f.read_text()))


def test_core_commands_are_core():
    reg = load_registry()
    for c in ["requirement", "design", "build", "test", "review", "verify"]:
        assert reg.commands[c]["maturity"] == "core"


def test_profile_resolution_pin_and_overrides():
    reg = load_registry()
    p = resolve_profile(reg, "enterprise@1.0.0", {"security.audit_logging": False})
    assert p["version"] == "1.0.0"
    assert "security.audit_logging" not in enabled_controls(p)
    assert p["overrides"] == {"security.audit_logging": False}
    with pytest.raises(ProfileError, match="version"):
        resolve_profile(reg, "enterprise@9.9.9")
    with pytest.raises(ProfileError, match="unknown setting"):
        resolve_profile(reg, "enterprise", {"security.nope": True})
    with pytest.raises(ProfileError, match="unknown profile"):
        resolve_profile(reg, "gold")


def test_stack_resolution():
    reg = load_registry()
    s = resolve_stack(reg, ["Java", "React", "PostgreSQL"])
    assert s["name"] == "java_react_postgres" and s["backend"]["framework"] == "Spring Boot"
    with pytest.raises(ProfileError):
        resolve_stack(reg, ["Cobol"])


def test_decision_models():
    reg = load_registry()
    assert set(reg.decision_models) == {"architecture_selection", "technology_selection", "risk_assessment",
                                        "trade_off_analysis", "root_cause_analysis", "evidence_verification",
                                        "reversibility_assessment"}
    for m in reg.decision_models.values():
        assert m["criteria"] and m["inputs"] and m["outputs"] and m["rules"]
