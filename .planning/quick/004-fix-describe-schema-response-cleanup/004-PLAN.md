---
phase: quick-004-fix-describe-schema-response-cleanup
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/bioimage_mcp/api/discovery.py
  - tests/contract/test_describe.py
  - tests/contract/test_discovery_contract.py
  - tests/contract/test_cellpose_meta_describe.py
autonomous: true

must_haves:
  truths:
    - "MCP describe() function responses do not include a top-level 'meta' field."
    - "MCP describe() function responses omit 'hints' keys when the value would be null (top-level and per-input)."
    - "MCP describe() function responses have single-line text for summary and descriptions (no literal \\n)."
  artifacts:
    - path: src/bioimage_mcp/api/discovery.py
      provides: "describe() response shaping/sanitization for FunctionDescriptor payloads"
    - path: tests/contract/test_describe.py
      provides: "contract coverage for describe() response fields"
    - path: tests/contract/test_discovery_contract.py
      provides: "field allowlist for describe() response"
  key_links:
    - from: src/bioimage_mcp/api/discovery.py
      to: "describe_function() return payload"
      via: "post-processing before return"
      pattern: "return\s+\{"
    - from: src/bioimage_mcp/api/discovery.py
      to: "params_schema.*description"
      via: "recursive sanitize of schema dict"
      pattern: "description"
---

<objective>
Clean up MCP describe() response payloads for LLM consumption by removing internal-only fields, normalizing whitespace in summary/description text, and omitting null hints.

Purpose: Reduce token waste and avoid awkward multi-line strings in introspection.
Output: Updated describe() response shaping + contract tests aligned with new response.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/bioimage_mcp/api/server.py
@src/bioimage_mcp/api/discovery.py
@tests/contract/test_describe.py
@tests/contract/test_discovery_contract.py
@tests/contract/test_cellpose_meta_describe.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Sanitize describe() function payload fields</name>
  <files>src/bioimage_mcp/api/discovery.py</files>
  <action>
Implement a small, local post-processing step for the function-node describe payload produced by DiscoveryService.describe_function:

- Remove the top-level 'meta' field from function describe responses.
- Omit 'hints' keys whenever their value would be None/null:
  - Top-level: only include 'hints' if non-None.
  - Per-input: only include inputs[port]['hints'] if non-None.
- Normalize human text fields to be single-line by replacing newlines with spaces:
  - Top-level: payload['summary']
  - Per-input: inputs[port]['description']
  - Per-output: outputs[port]['description'] (if present)
  - params_schema: recursively traverse dict/list and normalize any 'description' values that are strings.

Implementation constraints:
- Do not change semantic schema structure (types/required/properties) beyond the above field removals and text normalization.
- Prefer a small helper (e.g., _normalize_text and _sanitize_schema_descriptions) scoped inside src/bioimage_mcp/api/discovery.py to avoid cross-module churn.
  </action>
  <verify>pytest -q tests/contract/test_describe.py::test_describe_function_separates_inputs_outputs_params</verify>
  <done>
describe() for a function no longer returns 'meta'; any 'hints' fields with null values are absent; summary/description strings contain no literal '\n'.
  </done>
</task>

<task type="auto">
  <name>Task 2: Align contract tests with cleaned describe() response</name>
  <files>
tests/contract/test_describe.py
tests/contract/test_discovery_contract.py
tests/contract/test_cellpose_meta_describe.py
  </files>
  <action>
Update contract tests to match the new describe() response contract:

- Remove assertions that require 'meta' to exist in describe() function responses.
- Update any describe() allowed-keys sets to remove 'meta'.
- Add/extend a contract assertion that when no hints exist, 'hints' is omitted (not present with None).
- Add/extend a test case that injects newlines into:
  - the stored function description used as describe()['summary']
  - at least one params_schema property description (e.g., params_schema.properties.sigma.description)
  - and asserts the describe() response returns those fields with '\n' replaced by single spaces.

Keep the tests focused on the described cleanup behaviors; avoid introducing new dependencies or fixtures.
  </action>
  <verify>pytest -q tests/contract/test_describe.py tests/contract/test_discovery_contract.py tests/contract/test_cellpose_meta_describe.py</verify>
  <done>
Contract tests pass and encode the new response rules: no 'meta', no null 'hints', and no literal newlines in summary/description fields.
  </done>
</task>

<task type="auto">
  <name>Task 3: Run repo-level fast verification (lint + unit/contract)</name>
  <files>n/a</files>
  <action>
Run the fastest confidence checks to ensure the cleanup didn"t create regressions:
- ruff check .
- pytest -q tests/unit/ tests/contract/
  </action>
  <verify>ruff check . && pytest -q tests/unit/ tests/contract/</verify>
  <done>Lint passes and unit/contract tests pass locally.</done>
</task>

</tasks>

<verification>
- describe() outputs for at least one representative function ID contain no 'meta' key and no literal newlines in summary/description strings.
- For functions with no hints, no 'hints' keys appear in the response (top-level and per-input).
</verification>

<success_criteria>
- describe() responses are smaller/cleaner (no 'meta', no null 'hints') while keeping inputs/outputs/params_schema behavior intact.
- Contract coverage exists for newline normalization and null-hints omission.
</success_criteria>

<output>
After completion, create `.planning/quick/004-fix-describe-schema-response-cleanup/004-SUMMARY.md`
</output>
