import copy
import json

import pytest
from test_core_cli import version_1_ledger, version_2_ledger

from ai_claim_ledger.cli import main
from ai_claim_ledger.core import load_ledger, render_markdown, report


def test_shared_support_propagates_without_changing_truth_or_relations():
    data = version_2_ledger()
    data["sources"][0].update(reviewed_on="2026-01-01", review_due="2026-10-15")
    data["sources"][1].update(review_due="2026-01-01")
    original = copy.deepcopy(data)
    result = report(data, as_of="2026-10-15")
    assert result["source_review"]["overdue_claim_ids"] == ["c3", "c1"]
    rows = {row["claim_id"]: row for row in result["source_review"]["claims"]}
    assert rows["c1"]["overdue_supporting_sources"] == ["python-json"]
    assert rows["c2"]["overdue_supporting_sources"] == []
    assert rows["c3"]["overdue_supporting_sources"] == ["python-json"]
    assert data == original
    assert result["claims"] == report(data)["claims"]
    assert result["coverage"] == report(data)["coverage"]
    assert "source_review" not in report(data)
    assert "Claim statuses are unchanged" in render_markdown(result)


def test_boundaries_filters_undated_and_future_reviews():
    data = version_2_ledger()
    data["sources"][0]["review_due"] = "2024-02-29"
    assert report(data, as_of="2024-02-28")["source_review"]["overdue_claim_ids"] == []
    assert report(data, {"verified"}, as_of="2024-02-29")["source_review"]["overdue_claim_ids"] == [
        "c1"
    ]
    data["sources"][0] = {k: v for k, v in data["sources"][0].items() if k != "review_due"}
    data["sources"][0]["reviewed_on"] = "2026-10-16"
    row = report(data, {"verified"}, as_of="2026-10-15")["source_review"]["claims"][0]
    assert row["undated_supporting_sources"] == ["python-json"]
    assert row["reviewed_after_as_of"] == ["python-json"]


@pytest.mark.parametrize(
    "value",
    [
        "2026-02-29",
        "2026-2-01",
        "20261015",
        "2026-10-15T00:00:00Z",
        "0000-01-01",
        None,
        True,
        20261015,
    ],
)
def test_invalid_dates_reject_in_loader_and_boundary(tmp_path, value):
    data = version_2_ledger()
    data["sources"][0]["review_due"] = value
    path = tmp_path / "claims.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_ledger(path)
    with pytest.raises(ValueError):
        report(version_2_ledger(), as_of=value if value is not None else "bad")


def test_review_order_and_version_one_inline_sources(tmp_path):
    data = version_1_ledger()
    data["claims"][0]["sources"][0].update(reviewed_on="2026-10-15", review_due="2026-10-14")
    path = tmp_path / "claims.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="precedes"):
        load_ledger(path)
    data["claims"][0]["sources"][0]["review_due"] = "2026-10-15"
    path.write_text(json.dumps(data))
    loaded = load_ledger(path)
    result = report(loaded, as_of="2026-10-15")
    assert result["source_review"]["overdue_claim_ids"] == ["c1"]
    row = next(x for x in result["source_review"]["claims"] if x["claim_id"] == "c1")
    assert row["overdue_supporting_sources"] == ["0"]


def test_cli_dates_and_source_preservation(tmp_path, capsys):
    data = version_2_ledger()
    data["sources"][0]["review_due"] = "2026-10-15"
    path = tmp_path / "claims.json"
    path.write_text(json.dumps(data))
    original = path.read_bytes()
    assert main([str(path), "--format", "json", "--as-of", "2026-10-15"]) == 0
    assert json.loads(capsys.readouterr().out)["source_review"]["overdue_claim_ids"] == ["c3", "c1"]
    assert main([str(path), "--as-of", "bad"]) == 2
    assert path.read_bytes() == original
