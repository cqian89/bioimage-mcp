---
status: diagnosed
trigger: "Diagnose Phase 25 UAT gap #3 in /mnt/c/Users/meqia/bioimage-mcp."
created: 2026-03-06T16:01:33+08:00
updated: 2026-03-06T16:08:27+08:00
---

## Current Focus

hypothesis: `handle_tttr_write_spc132_events` and the sibling HHT3 export wrapper call SWIG-exposed tttrlib APIs as normal bound methods even though upstream requires an explicit `tttr` argument.
test: Compare the wrapper calls in `entrypoint.py` against the live tttrlib method signatures, then inspect tests and smoke coverage for why the mismatch was not detected.
expecting: The live signature will include a second positional `tttr` argument, while mocks/tests only model a single `path` parameter and never run a positive SPC export path.
next_action: return root-cause diagnosis and missing changes

## Symptoms

expected: Valid in-sandbox export path `exports/m1_copy.spc` succeeds after validation.
actual: Wrong extension and path escape are rejected correctly, but valid export fails with `TTTR.write_spc132_events() missing 1 required positional argument: 'tttr'`.
errors: `TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN`; `TTTRLIB_UNSAFE_OUTPUT_PATH`; `TTTR.write_spc132_events() missing 1 required positional argument: 'tttr'`
reproduction: Invoke the TTTR export flow with invalid patterns and then with valid `exports/m1_copy.spc`; observe validator rejections for invalid inputs and runtime TypeError for the valid path.
started: Reported in Phase 25 UAT gap #3 summary.

## Eliminated

## Evidence

- timestamp: 2026-03-06T16:03:00+08:00
  checked: .planning/phases/25-add-missing-tttr-methods/25-UAT.md
  found: Test 3 records correct guardrail failures for wrong extension and path escape, but valid `exports/m1_copy.spc` fails with `TTTR.write_spc132_events() missing 1 required positional argument: 'tttr'`.
  implication: Validation is working; the failure occurs only after the valid export path reaches the runtime write call.

- timestamp: 2026-03-06T16:04:00+08:00
  checked: tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py
  found: `handle_tttr_write_spc132_events()` validates `.spc` then calls `tttr.write_spc132_events(str(filepath))`; `handle_tttr_write_hht3v2_events()` does the analogous single-arg call.
  implication: The wrappers assume both specialized export routines behave like ordinary bound instance methods.

- timestamp: 2026-03-06T16:05:00+08:00
  checked: live tttrlib signatures in `bioimage-mcp-tttrlib` (`inspect.signature`)
  found: `TTTR.write_hht3v2_events` and `TTTR.write_spc132_events` both expose signature `(self, fp, tttr)` while `write` and `write_header` do not.
  implication: Calling the specialized writers with only the filepath leaves the required `tttr` positional argument unset, producing the exact UAT TypeError; the HHT3 wrapper has the same latent bug.

- timestamp: 2026-03-06T16:06:00+08:00
  checked: tests/unit/test_tttrlib_entrypoint_tttr_methods.py and tests/smoke/test_tttrlib_live.py search
  found: `_FakeTTTRWriter.write_hht3v2_events` and `.write_spc132_events` accept only `path`; the tests cover HHT3 success, unsafe path rejection, and wrong-extension rejection, but there is no successful SPC export test and no smoke coverage for either specialized writer.
  implication: The unit doubles encode the wrong API shape and coverage never executes a real positive specialized export path, so the signature mismatch shipped undetected.

- timestamp: 2026-03-06T16:08:00+08:00
  checked: `pytest tests/unit/test_tttrlib_entrypoint_tttr_methods.py -q`
  found: All 6 unit tests pass in the current workspace despite the live signature mismatch.
  implication: Existing automated coverage is insufficient to catch the real tttrlib specialized-writer API contract.

## Resolution

root_cause: `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py` calls `tttr.write_spc132_events(str(filepath))` as if it were a normal bound method, but the real tttrlib API signature is `(self, fp, tttr)`. The same mistake exists for `write_hht3v2_events`. The bug escaped because `tests/unit/test_tttrlib_entrypoint_tttr_methods.py` uses fake writer methods with the wrong one-argument signature and never exercises a successful SPC export, and there is no live smoke coverage for specialized write exports.
fix: Diagnose only; no source changes applied.
verification: Root cause confirmed by matching the UAT TypeError to the current wrapper call site and to live tttrlib signatures from the `bioimage-mcp-tttrlib` environment.
files_changed: []
