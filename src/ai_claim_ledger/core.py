from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

STATUSES = {"unverified", "needs-source", "verified", "disputed"}


def load_ledger(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("ledger must be a version 1 object")
    claims = data.get("claims")
    if not isinstance(claims, list):
        raise TypeError("claims must be a list")
    seen: set[str] = set()
    for index, claim in enumerate(claims, 1):
        if not isinstance(claim, dict):
            raise TypeError(f"claim {index} must be an object")
        claim_id, text, status = claim.get("id"), claim.get("claim"), claim.get("status")
        if not isinstance(claim_id, str) or not claim_id.strip() or claim_id in seen:
            raise ValueError(f"claim {index} has a missing or duplicate id")
        if not isinstance(text, str) or not text.strip() or status not in STATUSES:
            raise ValueError(f"claim {claim_id} requires text and a supported status")
        sources = claim.get("sources", [])
        if not isinstance(sources, list):
            raise TypeError(f"claim {claim_id} sources must be a list")
        for source in sources:
            if not isinstance(source, dict) or not isinstance(source.get("url"), str):
                raise TypeError(f"claim {claim_id} has an invalid source")
            parsed = urlparse(source["url"])
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"claim {claim_id} has an invalid source URL")
        if status == "verified" and not sources:
            raise ValueError(f"verified claim {claim_id} requires at least one source")
        seen.add(claim_id)
    return data


def report(data: dict[str, Any], statuses: set[str] | None = None) -> dict[str, Any]:
    if statuses and not statuses <= STATUSES:
        raise ValueError("unknown status filter")
    claims = [claim for claim in data["claims"] if not statuses or claim["status"] in statuses]
    claims.sort(key=lambda item: (item["status"], item["id"]))
    counts = Counter(item["status"] for item in claims)
    return {
        "version": 1,
        "total": len(claims),
        "counts": {status: counts.get(status, 0) for status in sorted(STATUSES)},
        "claims": claims,
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = ["# AI Claim Ledger", "", f"Claims in report: **{result['total']}**", ""]
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
            if claim.get("notes"):
                lines.append(f"  - Notes: {claim['notes']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
