---
status: investigating
trigger: "Investigate the 'TypeError: string indices must be integers, not 'str'' failure in 'base.scipy.signal.periodogram'. The error occurs during execution."
created: 2026-01-26T00:00:00Z
updated: 2026-01-26T00:00:00Z
---

## Current Focus

hypothesis: ANY_TO_TABLE inputs can be plain URI strings; periodogram path assumes dict/object artifacts and passes strings to table loader, leading to string indexing errors
test: inspect scipy_signal periodogram handling and pandas table loader type guards
expecting: no string-handling in periodogram/pandas loader while ANY_TO_TABLE accepts TableRef/ObjectRef/BioImageRef
next_action: document diagnosis and fix plan

## Symptoms

expected: periodogram execution completes without TypeError
actual: TypeError: string indices must be integers, not 'str'
errors: TypeError: string indices must be integers, not 'str'
reproduction: run base.scipy.signal.periodogram tool
started: unknown

## Eliminated

## Evidence

- timestamp: 2026-01-26T00:00:00Z
  checked: src/bioimage_mcp/registry/dynamic/adapters/scipy_signal.py
  found: periodogram/welch path reads input via input_dict = dict(inputs) and accepts art_ref as dict/object only
  implication: any string artifact (URI/path) will pass through unvalidated and be treated as non-bioimage

- timestamp: 2026-01-26T00:00:00Z
  checked: src/bioimage_mcp/registry/loader.py (IOPattern.ANY_TO_TABLE)
  found: ANY_TO_TABLE allows input artifact types TableRef/BioImageRef/ObjectRef
  implication: callers may send serialized refs or URIs; adapter must handle or reject clearly

- timestamp: 2026-01-26T00:00:00Z
  checked: src/bioimage_mcp/registry/dynamic/adapters/pandas.py::_load_table
  found: table loader handles dicts and objects with uri/path, but has no explicit string handling
  implication: string inputs are not normalized and can trigger type errors in downstream access

## Resolution

root_cause: "ANY_TO_TABLE periodogram path can receive a string artifact (URI/path) but scipy_signal/pandas table loading only handles dict/object refs; string inputs fall through and are later accessed like dicts, producing TypeError: string indices must be integers, not 'str'."
fix: ""
verification: ""
files_changed: []
