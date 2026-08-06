import json

import pytest

from ai_claim_ledger.cli import main
from ai_claim_ledger.core import load_ledger, render_markdown, report


def version_1_ledger():
    return {
        "version": 1,
        "claims": [
            {
                "id": "c1",
                "claim": "Python includes a standard JSON encoder and decoder.",
                "status": "verified",
                "sources": [
                    {
                        "url": "https://docs.python.org/3/library/json.html",
                        "title": "Python JSON documentation",
                    }
                ],
            },
            {
                "id": "c2",
                "claim": "The library is always installed.",
                "status": "disputed",
                "notes": "Not present in a clean environment.",
            },
        ],
    }


def version_2_ledger():
    return {
        "version": 2,
        "sources": [
            {
                "id": "python-json",
                "url": "https://docs.python.org/3/library/json.html",
                "title": "Python JSON documentation",
            },
            {
                "id": "python-downloads",
                "url": "https://www.python.org/downloads/",
                "title": "Python downloads",
            },
            {"id": "unused", "url": "https://docs.python.org/3/"},
        ],
        "claims": [
            {
                "id": "c1",
                "claim": "Python includes a standard JSON encoder and decoder.",
                "status": "verified",
                "evidence": [{"source_id": "python-json", "relation": "supports"}],
            },
            {
                "id": "c2",
                "claim": "The library is always installed.",
                "status": "disputed",
                "evidence": [{"source_id": "python-downloads", "relation": "context"}],
            },
            {
                "id": "c3",
                "claim": "The documentation covers every deployment.",
                "status": "unverified",
                "evidence": [
                    {"source_id": "python-json", "relation": "supports"},
                    {"source_id": "python-downloads", "relation": "contradicts"},
                ],
            },
        ],
    }


def test_version_1_report_remains_compatible():
    result = report(version_1_ledger(), {"verified"})
    assert result["version"] == 1
    assert result["total"] == 1
    assert "coverage" not in result
    assert (
        "[Python JSON documentation](https://docs.python.org/3/library/json.html)"
        in render_markdown(result)
    )
    with pytest.raises(ValueError, match="unknown"):
        report(version_1_ledger(), {"maybe"})


def test_version_2_relationships_and_coverage(tmp_path):
    path = tmp_path / "claims.json"
    path.write_text(json.dumps(version_2_ledger()), encoding="utf-8")
    data = load_ledger(path)
    result = report(data)
    assert result["version"] == 2
    assert result["coverage"] == {
        "unused_sources": ["unused"],
        "disputed_without_contradiction": ["c2"],
        "conflicting_evidence": ["c3"],
    }
    markdown = render_markdown(result)
    assert "Supports: [Python JSON documentation]" in markdown
    assert "Contradicts: [Python downloads]" in markdown
    assert "Unused sources: unused" in markdown


def test_version_2_clean_coverage_message():
    data = version_2_ledger()
    data["sources"] = data["sources"][:2]
    data["claims"][1]["evidence"] = [{"source_id": "python-downloads", "relation": "contradicts"}]
    data["claims"][2]["evidence"] = [{"source_id": "python-json", "relation": "context"}]
    assert "No evidence coverage gaps detected." in render_markdown(report(data))


def test_version_1_validation(tmp_path):
    path = tmp_path / "claims.json"
    path.write_text(json.dumps(version_1_ledger()), encoding="utf-8")
    assert load_ledger(path)["claims"][0]["id"] == "c1"
    bad = version_1_ledger()
    bad["claims"][0]["sources"] = []
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="requires"):
        load_ledger(path)


@pytest.mark.parametrize(
    ("mutate", "error", "message"),
    [
        (lambda data: data.update(version=3), ValueError, "version 1 or version 2"),
        (lambda data: data.update(sources={}), TypeError, "sources must be a list"),
        (lambda data: data["sources"].append(dict(data["sources"][0])), ValueError, "duplicate id"),
        (lambda data: data["sources"][0].update(url="file:///tmp/a"), ValueError, "source URL"),
        (lambda data: data["sources"][0].update(title=4), TypeError, "source title"),
        (lambda data: data["claims"][0].update(sources=[]), ValueError, "must use evidence"),
        (lambda data: data["claims"][0].update(evidence={}), TypeError, "evidence must be a list"),
        (
            lambda data: data["claims"][0]["evidence"][0].update(source_id="missing"),
            ValueError,
            "unknown source",
        ),
        (
            lambda data: data["claims"][0]["evidence"][0].update(relation="mentions"),
            ValueError,
            "unsupported evidence relation",
        ),
        (
            lambda data: data["claims"][0]["evidence"].append(
                {"source_id": "python-json", "relation": "context"}
            ),
            ValueError,
            "more than once",
        ),
        (
            lambda data: data["claims"][0].update(
                evidence=[{"source_id": "python-json", "relation": "context"}]
            ),
            ValueError,
            "supporting evidence",
        ),
    ],
)
def test_rejects_invalid_version_2_ledgers(tmp_path, mutate, error, message):
    data = version_2_ledger()
    mutate(data)
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(error, match=message):
        load_ledger(path)


@pytest.mark.parametrize(
    ("payload", "error"),
    [
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
    ],
)
def test_rejects_invalid_version_1_claim_shapes(tmp_path, payload, error):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(error):
        load_ledger(path)


def test_cli_and_safe_output(tmp_path, capsys):
    path = tmp_path / "claims.json"
    path.write_text(json.dumps(version_2_ledger()), encoding="utf-8")
    assert main([str(path), "--format", "json", "--status", "disputed"]) == 0
    output = capsys.readouterr().out
    assert '"total": 1' in output
    assert '"unused_sources"' in output
    target = tmp_path / "report.md"
    target.write_text("keep", encoding="utf-8")
    assert main([str(path), "--output", str(target)]) == 2
