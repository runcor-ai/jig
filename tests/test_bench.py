from pathlib import Path

import yaml
from fixtures import REQUIREMENT

from lattice.bench import _extract_json, score, summarize
from lattice.config import load_registry

SUITE = yaml.safe_load((Path(__file__).resolve().parents[1] / "bench/suites/crm_requirements.yaml").read_text())


def test_score_fixture_requirement():
    s = score(REQUIREMENT, SUITE["evaluation"], load_registry())
    assert s["schema_compliant"]
    assert set(s["covered"]) == {"FR-01_create", "FR-02_view_search"}
    assert s["failure_category"] == "coverage" and not s["success"]


def test_score_unparseable_and_schema_failures():
    reg = load_registry()
    assert score(None, SUITE["evaluation"], reg)["failure_category"] == "no_parseable_output"
    assert score({"functional_requirements": []}, SUITE["evaluation"], reg)["failure_category"] == "schema"


def test_extract_json_from_fenced_text():
    assert _extract_json('Here:\n```json\n{"a": 1}\n```') == {"a": 1}
    assert _extract_json('noise {"a": 2} trailing') == {"a": 2}
    assert _extract_json("no json") is None


def test_summarize_consistency():
    reg = load_registry()
    runs = [{"score": score(REQUIREMENT, SUITE["evaluation"], reg), "duration_ms": 10, "cost_usd": 0.1,
             "output_tokens": 5} for _ in range(3)]
    s = summarize(runs)
    assert s["consistency_covered_items_jaccard"] == 1.0 and s["task_success_rate"] == 0.0
    assert s["failure_categories"] == {"coverage": 3}
