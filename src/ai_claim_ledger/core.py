from __future__ import annotations

import html
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

STATUSES = {"unverified", "needs-source", "verified", "disputed"}
RELATIONS = {"supports", "contradicts", "context"}


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _text(value: str) -> str:
    """Keep supplied text literal in a single Markdown line."""
    value = html.escape(" ".join(value.splitlines()), quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+.!|~>-])", r"\\\1", value)


def _url(value: str) -> str:
    return quote(value, safe=":/?#@!$&'*+,;=%[]")


def load_ledger(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_object)
    if (
        not isinstance(data, dict)
        or type(data.get("version")) is not int
        or data["version"] not in {1, 2}
    ):
        raise ValueError("ledger must be a version 1 or version 2 object")
    claims = data.get("claims")
    if not isinstance(claims, list):
        raise TypeError("claims must be a list")
    if data["version"] == 1:
        _validate_version_1(claims)
    else:
        _validate_version_2(data, claims)
    return data


def _validate_version_1(claims: list[Any]) -> None:
    seen: set[str] = set()
    for index, claim in enumerate(claims, 1):
        claim_id, status = _validate_claim(claim, index, seen)
        if "evidence" in claim:
            raise ValueError(f"version 1 claim {claim_id} must use inline sources")
        sources = claim.get("sources", [])
        if not isinstance(sources, list):
            raise TypeError(f"claim {claim_id} sources must be a list")
        for source in sources:
            _validate_source(source, f"claim {claim_id}", require_id=False)
        if status == "verified" and not sources:
            raise ValueError(f"verified claim {claim_id} requires at least one source")
        seen.add(claim_id)


def _validate_version_2(data: dict[str, Any], claims: list[Any]) -> None:
    sources = data.get("sources")
    if not isinstance(sources, list):
        raise TypeError("version 2 sources must be a list")
    source_ids: set[str] = set()
    for index, source in enumerate(sources, 1):
        source_id = _validate_source(source, f"source {index}", require_id=True)
        if source_id in source_ids:
            raise ValueError(f"source {index} has a duplicate id")
        source_ids.add(source_id)

    claim_ids: set[str] = set()
    for index, claim in enumerate(claims, 1):
        claim_id, status = _validate_claim(claim, index, claim_ids)
        if "sources" in claim:
            raise ValueError(f"version 2 claim {claim_id} must use evidence relationships")
        evidence = claim.get("evidence", [])
        if not isinstance(evidence, list):
            raise TypeError(f"claim {claim_id} evidence must be a list")
        linked_sources: set[str] = set()
        relations: set[str] = set()
        for link in evidence:
            if not isinstance(link, dict):
                raise TypeError(f"claim {claim_id} has an invalid evidence relationship")
            source_id, relation = link.get("source_id"), link.get("relation")
            if not isinstance(source_id, str) or source_id not in source_ids:
                raise ValueError(f"claim {claim_id} references an unknown source")
            if not isinstance(relation, str) or relation not in RELATIONS:
                raise ValueError(f"claim {claim_id} has an unsupported evidence relation")
            if source_id in linked_sources:
                raise ValueError(f"claim {claim_id} links source {source_id} more than once")
            linked_sources.add(source_id)
            relations.add(relation)
        if status == "verified" and "supports" not in relations:
            raise ValueError(f"verified claim {claim_id} requires supporting evidence")
        claim_ids.add(claim_id)


def _validate_claim(claim: Any, index: int, seen: set[str]) -> tuple[str, str]:
    if not isinstance(claim, dict):
        raise TypeError(f"claim {index} must be an object")
    claim_id, text, status = claim.get("id"), claim.get("claim"), claim.get("status")
    if not isinstance(claim_id, str) or not claim_id.strip() or claim_id in seen:
        raise ValueError(f"claim {index} has a missing or duplicate id")
    if (
        not isinstance(text, str)
        or not text.strip()
        or not isinstance(status, str)
        or status not in STATUSES
    ):
        raise ValueError(f"claim {claim_id} requires text and a supported status")
    if "notes" in claim and not isinstance(claim["notes"], str):
        raise TypeError(f"claim {claim_id} notes must be a string")
    return claim_id, status


def _validate_source(source: Any, label: str, *, require_id: bool) -> str:
    if not isinstance(source, dict) or not isinstance(source.get("url"), str):
        raise TypeError(f"{label} has an invalid source")
    parsed = urlparse(source["url"])
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or any(char.isspace() or ord(char) < 32 for char in source["url"])
    ):
        raise ValueError(f"{label} has an invalid source URL")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ValueError(f"{label} has an invalid source URL port") from exc
    if "title" in source and not isinstance(source["title"], str):
        raise TypeError(f"{label} has an invalid source title")
    _validate_review_dates(source, label)
    if not require_id:
        return ""
    source_id = source.get("id")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError(f"{label} requires an id")
    return source_id


def _review_date(value: Any, label: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError(f"{label} must be a YYYY-MM-DD date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid calendar date") from exc


def _validate_review_dates(source: dict[str, Any], label: str) -> None:
    reviewed = (
        _review_date(source["reviewed_on"], f"{label} reviewed_on")
        if "reviewed_on" in source
        else None
    )
    due = (
        _review_date(source["review_due"], f"{label} review_due")
        if "review_due" in source
        else None
    )
    if reviewed and due and due < reviewed:
        raise ValueError(f"{label} review_due precedes reviewed_on")


def source_review(data: dict[str, Any], claims: list[dict[str, Any]], as_of: str) -> dict[str, Any]:
    boundary = _review_date(as_of, "as-of")
    sources = (
        data.get("sources", [])
        if data["version"] == 2
        else [source for claim in data["claims"] for source in claim.get("sources", [])]
    )
    for source in sources:
        _validate_review_dates(source, "source")
    lookup = {source["id"]: source for source in sources} if data["version"] == 2 else {}
    rows = []
    for claim in claims:
        supporting = (
            [
                (link["source_id"], lookup[link["source_id"]])
                for link in claim.get("evidence", [])
                if link["relation"] == "supports"
            ]
            if data["version"] == 2
            else [(str(index), source) for index, source in enumerate(claim.get("sources", []))]
        )
        overdue, undated, future = [], [], []
        for reference, source in supporting:
            if (
                "reviewed_on" in source
                and _review_date(source["reviewed_on"], "reviewed_on") > boundary
            ):
                future.append(reference)
            if "review_due" not in source:
                undated.append(reference)
            elif _review_date(source["review_due"], "review_due") <= boundary:
                overdue.append(reference)
        rows.append(
            {
                "claim_id": claim["id"],
                "overdue_supporting_sources": sorted(overdue),
                "undated_supporting_sources": sorted(undated),
                "reviewed_after_as_of": sorted(future),
            }
        )
    return {
        "as_of": as_of,
        "due_boundary": "review_due <= as_of",
        "claims": rows,
        "overdue_claim_ids": [row["claim_id"] for row in rows if row["overdue_supporting_sources"]],
    }


def report(
    data: dict[str, Any], statuses: set[str] | None = None, *, as_of: str | None = None
) -> dict[str, Any]:
    if statuses and not statuses <= STATUSES:
        raise ValueError("unknown status filter")
    claims = [claim for claim in data["claims"] if not statuses or claim["status"] in statuses]
    claims.sort(key=lambda item: (item["status"], item["id"]))
    counts = Counter(item["status"] for item in claims)
    result: dict[str, Any] = {
        "version": data["version"],
        "total": len(claims),
        "counts": {status: counts.get(status, 0) for status in sorted(STATUSES)},
        "claims": claims,
    }
    if data["version"] == 2:
        result["sources"] = sorted(data["sources"], key=lambda item: item["id"])
        result["coverage"] = _evidence_coverage(data)
    if as_of is not None:
        result["source_review"] = source_review(data, claims, as_of)
    return result


def _evidence_coverage(data: dict[str, Any]) -> dict[str, list[str]]:
    used: set[str] = set()
    disputed_without_contradiction: list[str] = []
    conflicting_evidence: list[str] = []
    for claim in data["claims"]:
        relations = {link["relation"] for link in claim.get("evidence", [])}
        used.update(link["source_id"] for link in claim.get("evidence", []))
        if claim["status"] == "disputed" and "contradicts" not in relations:
            disputed_without_contradiction.append(claim["id"])
        if {"supports", "contradicts"} <= relations:
            conflicting_evidence.append(claim["id"])
    return {
        "unused_sources": sorted(
            source["id"] for source in data["sources"] if source["id"] not in used
        ),
        "disputed_without_contradiction": sorted(disputed_without_contradiction),
        "conflicting_evidence": sorted(conflicting_evidence),
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = ["# AI Claim Ledger", "", f"Claims in report: **{result['total']}**", ""]
    source_lookup = {source["id"]: source for source in result.get("sources", [])}
    for status in sorted(STATUSES):
        claims = [claim for claim in result["claims"] if claim["status"] == status]
        if not claims:
            continue
        lines.extend([f"## {status.replace('-', ' ').title()} ({len(claims)})", ""])
        for claim in claims:
            lines.append(f"- [ ] **{_text(claim['id'])}** — {_text(claim['claim'])}")
            for source in claim.get("sources", []):
                label = source.get("title") or source["url"]
                lines.append(f"  - Source: [{_text(label)}]({_url(source['url'])})")
            for link in claim.get("evidence", []):
                source = source_lookup[link["source_id"]]
                label = source.get("title") or source["url"]
                relation = link["relation"].replace("-", " ").title()
                lines.append(f"  - {relation}: [{_text(label)}]({_url(source['url'])})")
            if claim.get("notes"):
                lines.append(f"  - Notes: {_text(claim['notes'])}")
        lines.append("")
    if "coverage" in result:
        lines.extend(["## Evidence Coverage", ""])
        coverage = result["coverage"]
        labels = {
            "unused_sources": "Unused sources",
            "disputed_without_contradiction": "Disputed claims without contradictory evidence",
            "conflicting_evidence": "Claims with supporting and contradictory evidence",
        }
        gaps = False
        for key, label in labels.items():
            if coverage[key]:
                gaps = True
                lines.append(f"- {label}: {', '.join(_text(value) for value in coverage[key])}")
        if not gaps:
            lines.append("No evidence coverage gaps detected.")
        lines.append("")
    if "source_review" in result:
        review = result["source_review"]
        lines.extend(
            [
                "## Source Review",
                "",
                f"As of {review['as_of']}; due dates on or before this date need review. Claim statuses are unchanged.",
                "",
            ]
        )
        for row in review["claims"]:
            lines.append(
                f"- {_text(row['claim_id'])}: overdue supporting sources: {', '.join(_text(value) for value in row['overdue_supporting_sources']) or 'none'}; no review due date: {', '.join(_text(value) for value in row['undated_supporting_sources']) or 'none'}; reviewed after as-of: {', '.join(_text(value) for value in row['reviewed_after_as_of']) or 'none'}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
