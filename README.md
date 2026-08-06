# AI Claim Ledger

[![CI](https://github.com/loganpendragonmultiverse/ai-claim-ledger/actions/workflows/ci.yml/badge.svg)](https://github.com/loganpendragonmultiverse/ai-claim-ledger/actions/workflows/ci.yml)

AI Claim Ledger converts factual claims copied from an AI response into a portable source and verification checklist. Claims remain explicitly unverified, in need of a source, verified, or disputed. Version 2 ledgers keep reusable sources in one registry and record whether each source supports, contradicts, or provides context for a claim.

## Three-minute start

```bash
python -m pip install .
claim-ledger examples/claims.json
claim-ledger examples/claims.json --status needs-source --format json
```

Verified claims require at least one supporting relationship to a syntactically valid HTTP or HTTPS source. Reports group claims by status, retain notes and source labels, and flag unused sources, disputed claims without contradictory evidence, and claims that have both supporting and contradictory evidence. The same source can be linked to multiple claims without copying its URL and title. Existing version 1 ledgers remain supported.

Version 2 uses a top-level source registry and claim-level evidence links:

```json
{
  "version": 2,
  "sources": [
    {"id": "python-json", "url": "https://docs.python.org/3/library/json.html", "title": "Python JSON documentation"}
  ],
  "claims": [
    {
      "id": "claim-1",
      "claim": "Python includes a standard JSON encoder and decoder.",
      "status": "verified",
      "evidence": [{"source_id": "python-json", "relation": "supports"}]
    }
  ]
}
```

## Boundaries

This tool does not call an AI model, extract claims automatically, browse URLs, judge source quality, or decide whether a relationship label is correct. A valid URL or a `supports` label is not evidence of truth. The person reviewing the ledger remains responsible for opening authoritative sources, recording the relationship accurately, and updating the claim status.

Requires Python 3.10 or newer. Development checks use Ruff, pytest with branch coverage, and package builds.

Part of the [Logan Pendragon Forge open-source collection](https://www.loganpendragonforge.com/open-source/). Licensed under the [MIT License](LICENSE).
