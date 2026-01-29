# MCP Response Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Clean up MCP list/describe/run responses by standardizing on `id`, shortening summaries, and relocating hints to parameter-level fields.

**Architecture:** Normalize summary extraction at discovery time, remove redundant fields from list responses, map function-level hints into per-input hints, and update MCP tool request/response schemas to use `id` consistently.

**Tech Stack:** Python 3.13, Pydantic v2, MCP FastMCP

---

## Task 1: Normalize summaries and remove docstring noise

**Files:**
- Modify: `src/bioimage_mcp/registry/engine.py`
- Modify: `tests/unit/registry/test_introspection.py` (if summary extraction assertions exist)

**Step 1: Write/adjust failing test**

Ensure the summary stored in discovery is only the first line (no Parameters section).

```python
def test_summary_is_first_line_only():
    summary = extract_summary("Return phasor coordinates.\n\nParameters\n----------\n...")
    assert summary == "Return phasor coordinates."
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/registry/test_introspection.py -k summary -v`
Expected: FAIL (summary still includes parameters)

**Step 3: Implement summary normalization**

In `DiscoveryEngine._process_callable` and `_map_runtime_functions`:
- Prefer `summary` from runtime list entries
- When deriving from docstrings, take only the first non-empty line
- Normalize whitespace to single spaces

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/registry/test_introspection.py -k summary -v`
Expected: PASS

**Step 5: Commit**

Skip commit unless user requests.

---

## Task 2: Clean list/describe outputs and move hints to inputs

**Files:**
- Modify: `src/bioimage_mcp/registry/index.py`
- Modify: `src/bioimage_mcp/api/discovery.py`
- Modify: `src/bioimage_mcp/api/schemas.py`
- Modify: `tests/contract/test_xarray_functions.py` (list response shape)
- Modify: `tests/contract/test_discovery_contract.py` (describe/list expectations)

**Step 1: Write/adjust failing tests**

Assert list responses do not include `fn_id` or `full_path`, and that describe returns per-input hints.

```python
assert "fn_id" not in item
assert "full_path" not in item
assert "hints" in result["inputs"]["signal"]
assert "hints" not in result or result["hints"] in (None, {"success_hints": ..., "error_hints": ...})
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/contract/test_discovery_contract.py -k list -v`
Expected: FAIL (fields still present)

**Step 3: Implement response cleanup**

- In `ToolIndex._to_payload`, remove `fn_id`, `full_path`, and `introspection_source` from list payloads.
- In `DiscoveryService.list_tools`, stop re-adding `full_path` and `has_children` for backward compatibility.
- In `describe_function`, map `FunctionHints.inputs` into `inputs[port].hints` and drop redundant top-level hints when empty.
- Extend `InputHints` schema to include any fields needed (e.g., `supported_storage_types`, `preprocessing_hint`, `dimension_requirements`).

**Step 4: Run tests to verify they pass**

Run: `pytest tests/contract/test_discovery_contract.py -k list -v`
Expected: PASS

**Step 5: Commit**

Skip commit unless user requests.

---

## Task 3: Standardize MCP tool inputs and run outputs to `id`

**Files:**
- Modify: `src/bioimage_mcp/api/server.py`
- Modify: `src/bioimage_mcp/api/discovery.py`
- Modify: `src/bioimage_mcp/api/serializers.py`
- Modify: `src/bioimage_mcp/api/schemas.py`
- Modify: `tests/unit/api/test_server.py`
- Modify: `tests/contract/test_run_contract.py`

**Step 1: Write/adjust failing tests**

Update tests to call MCP tools with `id` instead of `fn_id` and to expect `id` in run responses.

```python
resp = run(id="base.phasorpy.phasor.phasor_from_signal", ...)
assert resp["id"] == "base.phasorpy.phasor.phasor_from_signal"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/api/test_server.py -k run -v`
Expected: FAIL (run expects fn_id)

**Step 3: Implement input/output standardization**

- Update MCP tool signatures: `describe(id=...)`, `run(id=...)` and remove `fn_id`/`fn_ids`.
- Update `DiscoveryService.describe_function` to accept `id`/`ids` and wire through.
- Update `RunResponseSerializer` to emit `id` instead of `fn_id`.
- Remove `fn_id` fields from API schema models (e.g., `NextStepHint`, `SuggestedFix`, legacy search/list models if referenced).

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/api/test_server.py -k run -v`
Expected: PASS

**Step 5: Commit**

Skip commit unless user requests.
