import json

import pytest

from ai_claim_ledger.cli import main
from ai_claim_ledger.core import load_ledger, render_markdown, report


def ledger():
    return {
        "version": 1,
        "claims": [
            {
                "id": "c1",
                "claim": "The format was introduced in 2020.",
                "status": "verified",
                "sources": [{"url": "https://example.com/spec", "title": "Specification"}],
            },
            {
                "id": "c2",
                "claim": "The library is always installed.",
                "status": "disputed",
                "notes": "Not present in a clean environment.",
            },
        ],
    }


def test_report_filter_and_markdown():
    result = report(ledger(), {"verified"})
    assert result["total"] == 1
    assert "[Specification](https://example.com/spec)" in render_markdown(result)
    with pytest.raises(ValueError, match="unknown"):
        report(ledger(), {"maybe"})


def test_validation(tmp_path):
    path = tmp_path / "claims.json"
    path.write_text(json.dumps(ledger()), encoding="utf-8")
    assert load_ledger(path)["claims"][0]["id"] == "c1"
    bad = ledger()
    bad["claims"][0]["sources"] = []
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="requires"):
        load_ledger(path)


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        ({"version": 2}, ValueError),
        ({"version": 1, "claims": {}}, TypeError),
        ({"version": 1, "claims": [None]}, TypeError),
        ({"version": 1, "claims": [{"id": "", "claim": "A", "status": "unverified"}]}, ValueError),
        ({"version": 1, "claims": [{"id": "a", "claim": "A", "status": "wrong"}]}, ValueError),
        (
            {
                "version": 1,
                "claims": [{"id": "a", "claim": "A", "status": "unverified", "sources": {}}],
            },
            TypeError,
        ),
        (
            {
                "version": 1,
                "claims": [{"id": "a", "claim": "A", "status": "unverified", "sources": [None]}],
            },
            TypeError,
        ),
        (
            {
                "version": 1,
                "claims": [
                    {
                        "id": "a",
                        "claim": "A",
                        "status": "unverified",
                        "sources": [{"url": "file:///tmp/a"}],
                    }
                ],
            },
            ValueError,
        ),
    ],
)
def test_rejects_invalid_claim_shapes(tmp_path, payload, error):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(error):
        load_ledger(path)


def test_cli_and_safe_output(tmp_path, capsys):
    path = tmp_path / "claims.json"
    path.write_text(json.dumps(ledger()), encoding="utf-8")
    assert main([str(path), "--format", "json", "--status", "disputed"]) == 0
    assert '"total": 1' in capsys.readouterr().out
    output = tmp_path / "report.md"
    output.write_text("keep", encoding="utf-8")
    assert main([str(path), "--output", str(output)]) == 2
