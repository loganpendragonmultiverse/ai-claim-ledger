from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

STATUSES = {"unverified", "needs-source", "verified", "disputed"}
RELATIONS = {"supports", "contradicts", "context"}


def load_ledger(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") not in {1, 2}:
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
            if relation not in RELATIONS:
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
    if not isinstance(text, str) or not text.strip() or status not in STATUSES:
        raise ValueError(f"claim {claim_id} requires text and a supported status")
    return claim_id, status


def _validate_source(source: Any, label: str, *, require_id: bool) -> str:
    if not isinstance(source, dict) or not isinstance(source.get("url"), str):
        raise TypeError(f"{label} has an invalid source")
    parsed = urlparse(source["url"])
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{label} has an invalid source URL")
    if "title" in source and not isinstance(source["title"], str):
        raise TypeError(f"{label} has an invalid source title")
    if not require_id:
        return ""
    source_id = source.get("id")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError(f"{label} requires an id")
    return source_id


def report(data: dict[str, Any], statuses: set[str] | None = None) -> dict[str, Any]:
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
            lines.append(f"- [ ] **{claim['id']}** — {claim['claim']}")
            for source in claim.get("sources", []):
                label = source.get("title") or source["url"]
                lines.append(f"  - Source: [{label}]({source['url']})")
            for link in claim.get("evidence", []):
                source = source_lookup[link["source_id"]]
                label = source.get("title") or source["url"]
                relation = link["relation"].replace("-", " ").title()
                lines.append(f"  - {relation}: [{label}]({source['url']})")
            if claim.get("notes"):
                lines.append(f"  - Notes: {claim['notes']}")
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
                lines.append(f"- {label}: {', '.join(coverage[key])}")
        if not gaps:
            lines.append("No evidence coverage gaps detected.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
