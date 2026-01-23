---
status: resolved
trigger: "session_replay incorrectly reports base environment as not installed, blocking workflow replay despite the environment being functional"
created: 2026-01-22T00:00:00Z
updated: 2026-01-22T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - session_replay uses invalid `conda run --dry-run` flag
test: Executed buggy command directly - failed with exit code 2
expecting: Command to fail because --dry-run is invalid for conda run
next_action: Apply fix - remove --dry-run flag or use env list --json pattern

## Symptoms

expected: session_replay should successfully replay the workflow when the base environment is installed and functional
actual: Returns ENVIRONMENT_MISSING error with status validation_failed, claiming base env is "not installed"
errors: |
  {
    "error": {
      "code": "ENVIRONMENT_MISSING",
      "details": [{
        "actual": "not installed",
        "expected": "installed environment: base",
        "hint": "Run 'bioimage-mcp install base' to install this environment",
        "path": "/steps/*/id"
      }],
      "message": "Environment 'base' not installed"
    },
    "status": "validation_failed"
  }
reproduction: Call session_replay with a workflow_ref that references base environment functions
started: Current behavior - the base environment IS verified working via bioimage-mcp list and base.io.bioimage.load function runs successfully

## Eliminated

- hypothesis: "env_name extraction from fn_id is wrong"
  evidence: "Verified env_name='base' correctly extracted from 'base.io.bioimage.load'"
  timestamp: 2026-01-22T00:05:00Z

## Evidence

- timestamp: 2026-01-22T00:01:00Z
  checked: ENVIRONMENT_MISSING error code usage in codebase
  found: Error defined in src/bioimage_mcp/api/errors.py, used in sessions.py tests
  implication: Need to trace where this error is generated in session_replay path

- timestamp: 2026-01-22T00:02:00Z
  checked: session_replay env validation code (sessions.py lines 400-418)
  found: Uses `conda run -n bioimage-mcp-{env_name} --dry-run python -c "print('ok')"`
  implication: --dry-run is NOT a valid conda run option

- timestamp: 2026-01-22T00:03:00Z
  checked: conda run --help
  found: No --dry-run option exists for conda run command
  implication: Command is malformed and always fails

- timestamp: 2026-01-22T00:04:00Z
  checked: Direct execution of buggy vs correct command
  found: |
    - `conda run -n bioimage-mcp-base --dry-run python -c "print('ok')"` returns exit code 2 (unrecognized argument)
    - `conda run -n bioimage-mcp-base python -c "print('ok')"` returns exit code 0 (works)
  implication: ROOT CAUSE CONFIRMED - --dry-run flag breaks the command

- timestamp: 2026-01-22T00:05:00Z
  checked: Correct env check pattern in install.py
  found: _env_exists() uses `[exe, "env", "list", "--json"]` to properly check envs
  implication: Can use either approach (remove --dry-run, or use env list --json)

## Resolution

root_cause: |
  sessions.py line 402-416 used `conda run -n bioimage-mcp-{env_name} --dry-run python -c "print('ok')"` 
  to check if environment is installed. However, `--dry-run` is NOT a valid option for `conda run`.
  This caused the command to ALWAYS fail with exit code 2, making env_installed = False for ALL environments.
  
fix: |
  1. Removed the invalid `--dry-run` flag from the subprocess.run command
  2. Extracted env check into a mockable `_env_installed()` method (similar to `_function_exists()`)
  3. Updated contract tests to mock `_env_installed` and fixed test expectations to match implementation
  
verification: |
  - All 24 session-related tests pass (unit + contract)
  - Direct test: `_env_installed("base")` returns True, `_env_installed("nonexistent")` returns False
  - Lint check passes
  
files_changed:
  - src/bioimage_mcp/api/sessions.py: Extracted _env_installed method, removed --dry-run flag
  - tests/contract/test_session_replay.py: Mock _env_installed, fix test expectations
