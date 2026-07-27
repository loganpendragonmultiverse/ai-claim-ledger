# AI Claim Ledger

[![CI](https://github.com/loganpendragonmultiverse/ai-claim-ledger/actions/workflows/ci.yml/badge.svg)](https://github.com/loganpendragonmultiverse/ai-claim-ledger/actions/workflows/ci.yml)

AI Claim Ledger converts factual claims copied from an AI response into a portable source and verification checklist. Claims remain explicitly unverified, in need of a source, verified, or disputed.

## Three-minute start

```bash
python -m pip install .
claim-ledger examples/claims.json
claim-ledger examples/claims.json --status needs-source --format json
```

Verified claims require at least one syntactically valid HTTP or HTTPS source. Reports group claims by status and retain notes and source labels. Input and output stay local.

## Boundaries

This tool does not call an AI model, extract claims automatically, browse URLs, judge source quality, or verify that a page supports a claim. A valid URL is not evidence of truth. The person reviewing the ledger remains responsible for opening authoritative sources and updating the status.

Requires Python 3.10 or newer. Development checks use Ruff, pytest with branch coverage, and package builds.

Part of the [Logan Pendragon Forge open-source collection](https://www.loganpendragonforge.com/open-source/). Licensed under the [MIT License](LICENSE).
