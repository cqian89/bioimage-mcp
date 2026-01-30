# Quick Task 004 Summary: Fix describe schema response cleanup

## Objective

Clean up MCP describe() response payloads for LLM consumption by removing internal-only fields, normalizing whitespace in summary/description text, and omitting null hints.

## Changes Made

### src/bioimage_mcp/api/discovery.py

- Added `_normalize_text()` helper: replaces `\n` with space in strings
- Added `_sanitize_schema_descriptions()` helper: recursively normalizes description fields in params_schema
- Removed `meta` block from describe() function responses (tool_version, introspection_source, callable_fingerprint, module)
- Modified `hints` handling: only include in response when non-null
- Applied text normalization to:
  - Top-level `summary`
  - Per-input `description`
  - Per-output `description`
  - All `description` fields in `params_schema` (recursive)

### tests/contract/test_describe.py

- Removed `meta` assertions from `test_describe_function_separates_inputs_outputs_params`
- Added new test `test_describe_function_sanitizes_text_and_hints`:
  - Verifies newline normalization in summary, inputs, outputs, and params_schema
  - Verifies null hints are omitted (not present with None value)
- Restored `test_describe_returns_not_found_for_invalid_id` (was accidentally removed)

### tests/contract/test_discovery_contract.py

- Removed `meta` from `allowed_keys` set in describe response validation

### tests/contract/test_cellpose_meta_describe.py

- Removed `meta` block assertions from `test_describe_objectref_in_inputs_block`

### tests/unit/api/test_list_function_metadata_fields.py

- Updated `test_list_describe_alignment` to verify `meta` is not in response

## Verification

```bash
# All modified tests pass
pytest tests/contract/test_describe.py tests/contract/test_discovery_contract.py \
       tests/contract/test_cellpose_meta_describe.py tests/unit/api/test_list_function_metadata_fields.py -v
# 16 passed

# Lint passes
ruff check src/bioimage_mcp/api/discovery.py
# All checks passed!
```

## Commit

- Hash: 9deb2d9
- Message: `feat(quick-004): clean describe() response for LLM consumption`
