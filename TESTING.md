# Testing

```bash
python -m pip install -e ".[dev]"
ruff format --check .
ruff check .
pytest
python -m build
```

The suite enforces 90% branch-aware coverage. Regression cases exercise invalid
JSON shapes, duplicate keys, optional detail types, literal Markdown rendering,
exclusive output creation, ordinary reports and explicit boundary modes. CI runs
Python 3.10 and 3.14 on Linux, Windows and macOS; local Linux verification alone
does not establish the other platforms.

Install each built wheel and source distribution in a separate fresh virtual
environment, outside the source checkout. Run `claim-ledger --help`, then run the
installed example with Markdown and JSON output and the documented boundary mode.
Confirm the documentation/example files are installed, source bytes remain intact
and malformed inputs return exit 2 without a traceback. Repeat acceptance against
the downloaded tag-workflow artifacts before publishing.

Run `python tools/verify_artifact.py dist/<archive>` for each wheel and source
archive. The script creates a fresh environment outside the checkout and checks
installed imports, documentation, examples, report modes and failure behavior.
