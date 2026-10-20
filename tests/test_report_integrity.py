import copy
import json

import pytest
from test_core_cli import version_2_ledger as ledger

from ai_claim_ledger.cli import main
from ai_claim_ledger.core import load_ledger, render_markdown, report


def write(tmp_path, data):
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.mark.parametrize("version", [True, False, 1.0, [], {}])
def test_versions_are_integers(tmp_path, version):
    data = ledger()
    data["version"] = version
    with pytest.raises(ValueError):
        load_ledger(write(tmp_path, data))


def test_duplicate_json_keys(tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text('{"version":1,"version":1,"claims":[]}')
    assert main([str(path)]) == 2
    assert "duplicate JSON key" in capsys.readouterr().err


def test_output_is_exclusive_even_for_dangling_symlink(tmp_path):
    path = write(tmp_path, ledger())
    original = path.read_bytes()
    output = tmp_path / "report.md"
    assert main([str(path), "--output", str(output)]) == 0
    content = output.read_bytes()
    assert main([str(path), "--output", str(output)]) == 2
    assert output.read_bytes() == content
    assert path.read_bytes() == original
    link = tmp_path / "link"
    missing = tmp_path / "missing"
    try:
        link.symlink_to(missing)
    except (OSError, NotImplementedError):
        return  # Windows runners may not grant symlink creation privileges.
    assert main([str(path), "--output", str(link)]) == 2
    assert not missing.exists()


def test_empty_ledger(tmp_path):
    data = ledger()
    data["claims"] = []
    data["sources"] = []
    result = report(load_ledger(write(tmp_path, data)))
    assert result["total"] == 0
    assert "Claims in report: **0**" in render_markdown(result)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["claims"][0].update(notes=[]),
        lambda d: d["claims"][0].update(status=[]),
        lambda d: d["claims"][0]["evidence"][0].update(relation={}),
        lambda d: d["sources"][0].update(url="https:// bad.test"),
        lambda d: d["sources"][0].update(url="https://:80/"),
        lambda d: d["sources"][0].update(url="https://example.test:bad/"),
        lambda d: d["sources"][0].update(url="https://example.test:70000/"),
        lambda d: d["sources"][0].update(id=" "),
        lambda d: d.update(claims=[d["claims"][0], copy.deepcopy(d["claims"][0])]),
    ],
)
def test_malformed_detail_fields(tmp_path, mutate):
    data = ledger()
    mutate(data)
    path = write(tmp_path, data)
    assert main([str(path)]) == 2


def test_markdown_is_literal_and_json_is_unchanged(tmp_path):
    data = ledger()
    data["claims"][0].update(claim="<script>bad</script>\n# Forged", notes="[click](javascript:x)")
    data["sources"][0].update(title="[unsafe]", url="https://docs.python.org/a_(b)")
    result = report(load_ledger(write(tmp_path, data)), as_of="2026-10-20")
    markdown = render_markdown(result)
    assert "<script>" not in markdown and "\n# Forged" not in markdown
    assert r"\[unsafe\]" in markdown
    assert "https://docs.python.org/a_%28b%29" in markdown
    assert result["claims"][-1]["claim"] == data["claims"][0]["claim"]
    assert result["claims"][-1]["notes"] == data["claims"][0]["notes"]
