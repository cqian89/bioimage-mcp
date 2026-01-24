---
status: resolved
trigger: "Investigate bioimage-mcp install trackpy regressions: base reinstall, numpy error, CLI break"
created: 2026-01-23T21:14:15+01:00
updated: 2026-01-23T21:20:00+01:00
---

## Current Focus
hypothesis: "The _env_exists function fails to handle non-JSON output (preamble/warnings) from mamba/conda, returning False erroneously, triggering a destructive reinstall."
test: "Reproduced with mocked dirty JSON output."
expecting: "Result: False"
next_action: "Report diagnosis"

## Symptoms
expected: "Install 'trackpy' without touching base environment if exists, and keep bioimage-mcp CLI working."
actual: "Re-installs base, fails with numpy error, breaks CLI."
errors: "Numpy build error (reported)"
reproduction: "Run 'bioimage-mcp install trackpy' in an environment where mamba/conda prints warnings"
started: "Unknown"

## Eliminated
- hypothesis: "_env_exists checks wrong name"
  evidence: "Path parsing is correct"
  timestamp: "2026-01-23T21:18:00+01:00"

## Evidence
- timestamp: "2026-01-23T21:16:00+01:00"
  checked: "src/bioimage_mcp/bootstrap/install.py"
  found: "_env_exists calls json.loads(proc.stdout) without cleaning"
  implication: "Any output before JSON causes parsing failure"
- timestamp: "2026-01-23T21:19:00+01:00"
  checked: "reproduction script"
  found: "mocked dirty JSON makes _env_exists return False"
  implication: "Confirmed root cause"

## Resolution
root_cause: "_env_exists fails to parse mixed text/JSON output from conda/mamba, returning False. This triggers 'base' env update/reinstall. The update command (--prune) removes the editable CLI install, and subsequently fails on numpy build (Python 3.13 compat), leaving the environment broken."
fix: "Implement robust JSON extraction in _env_exists (find first '{')."
verification: "Unit test with dirty JSON should pass."
files_changed: []
