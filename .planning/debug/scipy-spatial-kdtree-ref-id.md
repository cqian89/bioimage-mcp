---
status: investigating
trigger: "Investigate the 'validation error for ObjectRef' failure in 'base.scipy.spatial.cKDTree'. The error is: '1 validation error for ObjectRef ... ref_id Input should be a valid string'. This suggests the 'ref_id' is missing from the returned ObjectRef. Steps: 1. Locate 'src/bioimage_mcp/registry/dynamic/adapters/scipy_spatial.py'. 2. Examine the '_execute_kdtree_build' method and how it constructs the returned artifact. 3. Verify if 'ref_id' is being populated in the 'ObjectRef'. 4. Produce a diagnosis and a fix plan in '.planning/debug/scipy-spatial-kdtree-ref-id.md'."
created: 2026-01-26T19:27:47Z
updated: 2026-01-26T19:28:58Z
---

## Current Focus

hypothesis: ObjectRef is built without a valid ref_id in _execute_kdtree_build.
test: Document missing ref_id and compare with other adapters that set ref_id.
expecting: _execute_kdtree_build returns dict lacking ref_id while ObjectRef schema requires it.
next_action: Record evidence for missing ref_id and outline fix plan.

## Symptoms

expected: base.scipy.spatial.cKDTree returns ObjectRef with valid ref_id string.
actual: Validation error: "1 validation error for ObjectRef ... ref_id Input should be a valid string".
errors: "1 validation error for ObjectRef ... ref_id Input should be a valid string".
reproduction: Invoke base.scipy.spatial.cKDTree; error occurs on ObjectRef validation.
started: unknown.

## Eliminated

## Evidence

- timestamp: 2026-01-26T19:28:58Z
  checked: src/bioimage_mcp/registry/dynamic/adapters/scipy_spatial.py::_execute_kdtree_build
  found: Returned ObjectRef dict includes type, python_class, uri, storage_type, metadata but no ref_id.
  implication: ObjectRef validation fails because ref_id is required by ArtifactRef schema.

- timestamp: 2026-01-26T19:28:58Z
  checked: src/bioimage_mcp/artifacts/models.py::ArtifactRef/ObjectRef
  found: ref_id is a required field; ObjectRef has no default for ref_id.
  implication: Any ObjectRef without ref_id triggers validation error.

- timestamp: 2026-01-26T19:28:58Z
  checked: src/bioimage_mcp/registry/dynamic/adapters/pandas.py::_execute_constructor
  found: ObjectRef creation includes explicit ref_id (uuid) alongside uri.
  implication: scipy_spatial adapter is inconsistent; should include ref_id like other adapters.

## Resolution

root_cause: ""
fix: ""
verification: ""
files_changed: []
