---
phase: quick-003-clean-up-stale-xfail-markers
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/unit/runtimes/test_workflow_validation.py
  - tests/integration/test_flim_calibration.py
autonomous: true

must_haves:
  truths:
    - "The previously XPASSing tests run as normal passing tests (no XPASS)."
    - "Targeted test runs for the two files pass without xfail markers."
    - "Full test suite passes with no regressions."
  artifacts:
    - path: "tests/unit/runtimes/test_workflow_validation.py"
      provides: "No stale @pytest.mark.xfail remaining for tests that now pass"
    - path: "tests/integration/test_flim_calibration.py"
      provides: "No stale @pytest.mark.xfail remaining for tests that now pass"
  key_links:
    - from: "tests/unit/runtimes/test_workflow_validation.py"
      to: "pytest"
      via: "test collection + execution"
      pattern: "@pytest\\.mark\\.xfail"
    - from: "tests/integration/test_flim_calibration.py"
      to: "pytest"
      via: "test collection + execution"
      pattern: "@pytest\\.mark\\.xfail"
---

<objective>
Remove stale xfail markers from tests that now pass.

Purpose: Keep the suite accurate by ensuring passing tests are not masked by legacy xfail decorators.
Output: Updated test files with xfail decorators removed and a clean test run (no XPASS).
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@tests/unit/runtimes/test_workflow_validation.py
@tests/integration/test_flim_calibration.py
</context>

<tasks>

<task type="auto">
  <name>Remove stale @pytest.mark.xfail decorators for XPASSing tests</name>
  <files>tests/unit/runtimes/test_workflow_validation.py, tests/integration/test_flim_calibration.py</files>
  <action>
1) In each target file, locate the specific test(s) currently marked with `@pytest.mark.xfail` that are now XPASSing.
   - If multiple `xfail` markers exist, only remove those associated with the XPASS from the provided test run context.
   - Prefer removing the decorator entirely; do not convert to `skip` or add new xfail conditions.

2) Remove the `@pytest.mark.xfail(...)` decorator line(s), and clean up any now-unused imports (e.g., `import pytest` only if it becomes unused).

3) Keep test intent intact: do not rewrite assertions or weaken coverage; this is marker cleanup only.
  </action>
  <verify>
python -m pytest tests/unit/runtimes/test_workflow_validation.py -q -rX
python -m pytest tests/integration/test_flim_calibration.py -q -rX
  </verify>
  <done>
Both files contain no stale xfail decorators for the formerly XPASSing tests, and each file runs with no XPASS reported.
  </done>
</task>

<task type="auto">
  <name>Run full test suite to confirm no regressions</name>
  <files>tests/unit/runtimes/test_workflow_validation.py, tests/integration/test_flim_calibration.py</files>
  <action>Run the full test suite after marker removal to ensure no new failures are introduced.</action>
  <verify>python -m pytest</verify>
  <done>Full suite completes successfully (exit code 0) and output contains no XPASS.</done>
</task>

</tasks>

<verification>
- Targeted runs for the two files show no XPASS (`-rX` shows xpasses).
- Full `pytest` run passes.
</verification>

<success_criteria>
- `tests/unit/runtimes/test_workflow_validation.py` no longer uses xfail to mask passing behavior.
- `tests/integration/test_flim_calibration.py` no longer uses xfail to mask passing behavior.
- CI-equivalent local run (`python -m pytest`) passes.
</success_criteria>

<output>
After completion, create `.planning/quick/003-clean-up-stale-xfail-markers/003-SUMMARY.md`
</output>
