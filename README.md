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

## Offline source review dates

Add optional `reviewed_on` and `review_due` dates to sources (strict `YYYY-MM-DD`,
with due on or after reviewed). Run `claim-ledger examples/claims.json --as-of 2026-10-15`.
There is no implicit current date. A due date on or before the explicit as-of boundary
is overdue. The source-review section flags claims linked to overdue **supporting**
sources; contradictory and contextual evidence does not create that flag. Shared
version 2 sources propagate to each linked claim. Undated supporting sources and
reviews recorded after the boundary are listed separately. Source-review rows follow
the status filter; coverage retains its existing whole-ledger meaning.

Version 1 inline sources are treated as supporting and referenced by zero-based index
within each claim; version 2 uses registry source IDs. Omitting `--as-of` preserves
the ordinary report structure. Review dates are validated even without an as-of check.
This is an administrative review checklist: an overdue source neither disproves nor
invalidates a claim. Statuses and evidence relations remain exactly as supplied, and
no URL is fetched. The report is not a reconstruction of a past ledger state.

## Input and report integrity

Schema versions must be JSON integers, and duplicate object keys are rejected rather
than silently replacing earlier values. Optional report details must have their
documented string/list types. Markdown displays supplied text literally, with line
breaks flattened; JSON retains validated source values. Output creation is exclusive:
existing files are refused and existing symbolic links are checked before creation.
This is accidental-overwrite protection, not a defense against concurrent hostile
filesystem changes. Reports remain offline and do not
modify their source ledger.

Python 3.10+ on Windows, macOS and Linux is covered by the required CI matrix.
Install a release wheel with `python -m pip install path/to/release.whl`. Installed
examples and instructions are under `share/doc/ai-claim-ledger` in the environment prefix.
The [testing guide](TESTING.md) documents checks and installed-artifact acceptance.
See [contributing](CONTRIBUTING.md), [support](SUPPORT.md), and [security](SECURITY.md)
for maintenance, issue and vulnerability reporting. This small tool is maintained
through reviewed changes; no automatic truth or story interpretation is promised.
