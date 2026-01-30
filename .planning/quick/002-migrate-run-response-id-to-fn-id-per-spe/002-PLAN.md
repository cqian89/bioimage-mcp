---
phase: quick
plan: 002
type: execute
wave: 1
depends_on: []
files_modified:
  - src/bioimage_mcp/api/serializers.py
  - src/bioimage_mcp/api/server.py
  - tests/unit/api/test_run_response_serializer.py
  - tests/integration/test_call_tool_dry_run.py
  - tests/integration/test_interactive_call_tool.py
  - tests/integration/test_interactive_errors.py
autonomous: true

must_haves:
  truths:
    - "MCP run responses include fn_id (not id) for the executed function"
    - "MCP run responses do not include session_id"
    - "Contract + integration tests asserting run responses pass without session_id"
  artifacts:
    - path: "src/bioimage_mcp/api/serializers.py"
      provides: "Run response serialization emits fn_id and omits session_id"
    - path: "src/bioimage_mcp/api/server.py"
      provides: "Run handler does not pass session_id into serialized run response"
    - path: "tests/unit/api/test_run_response_serializer.py"
      provides: "Unit coverage for run serializer output keys"
    - path: "tests/integration/test_interactive_call_tool.py"
      provides: "Integration assertions for run tool response shape"
  key_links:
    - from: "src/bioimage_mcp/api/serializers.py"
      to: "run tool result payload"
      via: "serialized dict keys"
      pattern: "\"fn_id\""
    - from: "tests/integration/test_*.py"
      to: "run response payload"
      via: "assertions on response keys"
      pattern: "session_id"
---

<objective>
Migrate MCP run tool responses to use `fn_id` instead of `id` and remove `session_id` from run responses, per spec 023-run-response-optimization (FR-011, FR-012).

Purpose: Restore the intended run response contract and undo regressions from earlier commits.
Output: Updated run response serializer + handler wiring + updated unit/integration tests.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@specs/023-run-response-optimization/proposal.md
@specs/023-run-response-optimization/plan.md

@src/bioimage_mcp/api/serializers.py
@src/bioimage_mcp/api/server.py
@tests/unit/api/test_run_response_serializer.py
@tests/integration/test_call_tool_dry_run.py
@tests/integration/test_interactive_call_tool.py
@tests/integration/test_interactive_errors.py
</context>

<tasks>

<task type="auto">
  <name>Update run response serialization to emit fn_id and omit session_id</name>
  <files>src/bioimage_mcp/api/serializers.py</files>
  <action>
Change the run response serializer so run responses contain `fn_id` (with the same value previously emitted as `id`) and never include `session_id`.

Implementation requirements:
- Replace the serialized key `id` with `fn_id` for run responses.
- Remove any conditional inclusion of `session_id` in the serialized run response.
- Do not change MCP request input: `run(id=...)` remains the request parameter (this change is response-only).
- Do not modify list/search/describe serializers; only the run response shape changes.
  </action>
  <verify>pytest tests/unit/api/test_run_response_serializer.py -v</verify>
  <done>
Unit test coverage reflects the new keys: run response includes `fn_id`, and `session_id` is absent.
  </done>
</task>

<task type="auto">
  <name>Stop passing session_id through the run handler result payload</name>
  <files>src/bioimage_mcp/api/server.py</files>
  <action>
Update the MCP server run handler so it no longer injects `session_id` into the base result payload that is handed to the run response serializer.

Rationale: The serializer should not need session context for run responses, and the run response must not emit `session_id` per FR-012.
  </action>
  <verify>pytest tests/contract/test_run.py -v</verify>
  <done>
Contract tests for the run tool pass with the updated response payload shape.
  </done>
</task>

<task type="auto">
  <name>Update integration tests and verify no downstream assumptions</name>
  <files>
tests/integration/test_call_tool_dry_run.py
tests/integration/test_interactive_call_tool.py
tests/integration/test_interactive_errors.py
  </files>
  <action>
Update integration tests to match the new run response contract:
- Remove any assertions expecting `session_id` to be present in run responses.
- If any tests assert on run response key `id`, update them to assert `fn_id` instead.

Then verify there are no remaining references that treat run responses as having `id` or `session_id`:
- Use ripgrep searches for `result["id"]` and `response["session_id"]` (excluding workflow step JSON where applicable).

Important: Do NOT modify session export tests (session export responses are not run responses).
  </action>
  <verify>
rg 'result\["id"\]' src tests -g'*.py' | rg -v 'steps'
rg 'response\["session_id"\]' tests -g'*.py'
pytest tests/integration/test_interactive_call_tool.py -v
pytest tests/integration/test_call_tool_dry_run.py -v
pytest tests/integration/test_interactive_errors.py -v
pytest tests/ -v
ruff check .
ruff format --check .
  </verify>
  <done>
- Integration tests that validate run responses no longer assert `session_id`.
- Test suite + ruff checks pass with the updated run response contract.
  </done>
</task>

</tasks>

<verification>
- Run response payload includes `fn_id` and omits `session_id` across unit, contract, and integration tests.
- No remaining code/test paths access run responses via `result["id"]` or `response["session_id"]` (outside workflow step IDs).
</verification>

<success_criteria>
- `pytest tests/unit/api/test_run_response_serializer.py -v` passes
- `pytest tests/contract/test_run.py -v` passes
- `pytest tests/integration/test_interactive_call_tool.py -v` passes
- `pytest tests/integration/test_call_tool_dry_run.py -v` passes
- `pytest tests/integration/test_interactive_errors.py -v` passes
- `pytest tests/ -v` passes
- `ruff check .` and `ruff format --check .` pass
</success_criteria>

<output>
After completion, create `.planning/quick/002-migrate-run-response-id-to-fn-id-per-spe/002-SUMMARY.md`
</output>
