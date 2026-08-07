# Changelog

## 1.1.0 - 2026-08-06

- Added a version 2 ledger format with reusable source records and explicit `supports`,
  `contradicts`, and `context` relationships.
- Added evidence-coverage reporting for unused sources, disputed claims without contradictory
  evidence, and claims with conflicting evidence.
- Preserved validation and reporting for existing version 1 ledgers.

## 1.0.1 - 2026-07-26

- Replaced placeholder source URLs in the sample and tests with primary Python documentation.

## 1.0.0 - 2026-07-26

- Added structured claim, source, note, and verification-status records.
- Added source URL validation and evidence requirements for verified claims.
- Added filtered Markdown checklists and JSON reports.
