---
status: resolved
trigger: "Diagnose Phase 25 UAT gap #5 in /mnt/c/Users/meqia/bioimage-mcp."
created: 2026-03-06T00:00:00Z
updated: 2026-03-06T08:08:10Z
---

## Current Focus

hypothesis: confirmed: `handle_correlator_get_curve()` tuple-unpacks a non-iterable SWIG `CorrelatorCurve`, and correlator getter handlers return a thinner/inconsistent `TableRef` shape than the constructor path.
test: compare live tttrlib runtime behavior against `entrypoint.py`, unit tests, schema, manifest, and smoke coverage.
expecting: runtime inspection and tests explain the `get_curve` crash and show why `get_corr` inconsistency was not caught before UAT.
next_action: return concise diagnosis with impacted files and missing fixes.

## Symptoms

expected: `tttrlib.Correlator` methods return consistent `TableRef` outputs with stable tau/correlation naming and `get_curve` succeeds.
actual: constructor, `get_x_axis`, and `get_corr` succeed, but `get_curve` fails with `cannot unpack non-iterable CorrelatorCurve object`; `get_corr` metadata/column naming appears inconsistent.
errors: `cannot unpack non-iterable CorrelatorCurve object`; unsupported subset validation correctly reports `TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN` for `normalize=true`.
reproduction: run the Phase 25 UAT coverage for `tttrlib.Correlator` constructor and accessors, especially `get_curve` and `get_corr`.
started: observed during Phase 25 UAT gap analysis.

## Eliminated

## Evidence

- timestamp: 2026-03-06T08:08:10Z
  checked: `.planning/phases/25-add-missing-tttr-methods/25-UAT.md`
  found: UAT gap #5 reports constructor success, `get_x_axis` success, `get_corr` partial success with inconsistent metadata/column naming, and `get_curve` failure with `cannot unpack non-iterable CorrelatorCurve object`.
  implication: reproduction symptoms are specific to the Correlator getter-family implementation, not subset-validation or constructor wiring.

- timestamp: 2026-03-06T08:08:10Z
  checked: `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py`
  found: `handle_correlator_get_curve()` does `curve = correlator.get_curve(); tau, corr = curve`, while the constructor handler uses `correlator.x`/`correlator.y`. `get_curve`/`get_x_axis`/`get_corr` handlers also omit the richer `metadata.columns` block present in the constructor `TableRef`.
  implication: `get_curve` has a direct runtime-shape bug, and the getter-family artifact contract is inconsistent with the constructor path.

- timestamp: 2026-03-06T08:08:10Z
  checked: live tttrlib runtime in `bioimage-mcp-tttrlib`
  found: `correlator.get_curve()` returns `tttrlib.tttrlib.CorrelatorCurve`, `hasattr(curve, '__iter__') == False`, and the object exposes `.x`, `.y`, `get_x_axis()`, and `get_corr()`.
  implication: tuple-unpacking in `handle_correlator_get_curve()` must always fail against the real runtime; the correct access path is via object attributes/getters.

- timestamp: 2026-03-06T08:08:10Z
  checked: `tests/unit/test_tttrlib_entrypoint_clsm_methods.py` and `pytest tests/unit/test_tttrlib_entrypoint_clsm_methods.py -q`
  found: the only correlator getter unit test stubs `get_curve()` to return a Python tuple and asserts only CSV headers; there are no unit tests for `get_x_axis` or `get_corr`, and the mocked test suite still passes.
  implication: test doubles masked the real SWIG return type and left getter metadata/output consistency uncovered.

- timestamp: 2026-03-06T08:08:10Z
  checked: `tests/smoke/test_tttrlib_live.py`, `tools/tttrlib/manifest.yaml`, and `tools/tttrlib/schema/tttrlib_api.json`
  found: smoke coverage exercises `tttrlib.Correlator.get_curve` and `tttrlib.Correlator.get_x_axis` but not `tttrlib.Correlator.get_corr`; manifest/schema declare `get_corr` as a single-column `correlation` table, which differs from the constructor's richer `curve` metadata shape.
  implication: live coverage missed `get_corr`, and schema/handler consistency focuses on nominal shape rather than harmonized artifact metadata.

## Resolution

root_cause: `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py` implemented `tttrlib.Correlator.get_curve` as if `correlator.get_curve()` returned an iterable `(tau, corr)` tuple, but the real tttrlib runtime returns a non-iterable `CorrelatorCurve` object with `.x`/`.y` and getter methods. Separate getter handlers were also hand-built with thinner `TableRef` payloads than the constructor path, so `get_corr` lacks the richer metadata/column contract UAT expected.
fix: not applied (diagnosis only)
verification: inspected live tttrlib runtime object shape, reviewed handler/schema/manifest/test coverage, and confirmed the existing mocked unit test passes despite the real runtime mismatch.
files_changed: []
