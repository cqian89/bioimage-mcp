# Code Review Report: 023-run-response-optimization

**Branch**: `023-run-response-optimization`  
**Reviewed commit**: `91257e7` ("feat: implement verbosity-aware run response serialization and artifact cleanup")  
**Spec references**: `specs/023-run-response-optimization/plan.md`, `specs/023-run-response-optimization/proposal.md`

## Scope of Review

This review focuses on the implementation changes in the reviewed commit:

- `src/bioimage_mcp/api/server.py`
- `src/bioimage_mcp/api/serializers.py` (new)
- `src/bioimage_mcp/api/artifacts.py`
- `src/bioimage_mcp/artifacts/models.py`
- `src/bioimage_mcp/artifacts/store.py`
- Tests added/updated under `tests/unit/` and `tests/contract/`

It is intentionally scoped to changes relevant to **run response token optimization** and **ArtifactRef cleanup**.

## Spec Expectations (from plan/proposal)

The plan/proposal define several non-negotiable behaviors for this milestone:

1. **Verbosity control**: `run` supports `verbosity` with default `minimal`, and also `standard` and `full`.
2. **Default responses are summary-first**: minimal run responses should include only what’s needed for chaining and reasoning.
3. **Workflow record hiding**: workflow record should be hidden in `minimal`/`standard` and available only in `full`.
4. **Never inline log content in `run` responses**: even in `full`, avoid token explosions; use `artifact_info(text_preview_bytes=...)` instead.
5. **ArtifactRef cleanup**:
   - Remove top-level `ndim`, `dims`, `shape`, `dtype`, `physical_pixel_sizes` from `ArtifactRef`.
   - Keep dimension fields only inside `metadata`.
   - Ensure serialization excludes `None` fields and empty collections.
6. **Chaining safety**: `run` responses may omit `uri`, but tool execution must accept partial refs (e.g., dict with only `ref_id`).

## What the Implementation Gets Right

### ArtifactRef model cleanup is aligned

- `ArtifactRef` no longer has duplicated top-level dimension fields.
- `ArtifactRef.model_dump()` now enforces `exclude_none=True` and removes empty `checksums` and empty `metadata`.

This matches the intent described in the plan/proposal and reduces response payload size at the source.

### `artifact_info` adapts to the model change

- `ArtifactsService.artifact_info()` now reads `dims`/`ndim` from `ref.metadata` rather than `ref.dims/ref.ndim`.

### Chaining safety appears already supported in execution

Although not changed in this commit, current `ExecutionService` input preprocessing resolves:

- bare `ref_id` strings, and
- dict inputs containing `{"ref_id": ...}` even if `uri` is missing.

This is consistent with the plan’s “partial ref inflation” requirement.

### Tests added for key mechanics

- Serializer unit tests exist (`tests/unit/api/test_run_response_serializer.py`).
- ArtifactRef dump behavior tests exist (`tests/unit/artifacts/test_artifactref_dump.py`).
- Dimension consistency validation is covered (`tests/unit/artifacts/test_dimension_validation.py`).

These provide a useful baseline and should prevent some regressions.

## Findings

### 1) HIGH: Invalid `verbosity` silently escalates to `full`

**Why it matters**: If a client passes an invalid value (e.g., `verbosity="foo"`), the implementation currently falls into the `else` branch and returns **full output**. This creates two risks:

- accidental token explosion
- accidental inclusion of fields the spec explicitly tries to hide by default

**Where**:

- `src/bioimage_mcp/api/server.py` defines `verbosity: str = "minimal"` without validation.
- `src/bioimage_mcp/api/serializers.py` treats all values besides `minimal`/`standard` as `full`.

**Recommendation**:

- Validate `verbosity` explicitly (either in `server.run()` before calling the serializer, or in `RunResponseSerializer.serialize()`).
- Prefer coercing unknown values to `minimal` (token-safety default), or raise a structured validation error.
- Update the tool signature to use `Literal["minimal","standard","full"]` so invalid values are rejected early.

### 2) MEDIUM: Minimal/standard serialization likely omits `shape/dims/dtype` in real responses

**Why it matters**: After ArtifactRef cleanup, dimension data lives in `metadata`. However, the serializer currently reads `shape/dims/dtype` from the top-level output dict. In actual run outputs (based on `ArtifactRef.model_dump()`), these fields will not exist at top level.

That means minimal output can degrade into essentially:

- `ref_id`
- `type`
- (maybe) `size_mb`

…which does not meet the plan/proposal goal that minimal includes `shape`, `dims`, and `dtype` for chaining.

**Where**:

- `src/bioimage_mcp/api/serializers.py` uses `ref_dict.get("shape")`, `ref_dict.get("dims")`, `ref_dict.get("dtype")`.

**Additional complexity**: `InteractiveExecutionService.call_tool()` adds a `summary` field (and potentially `content` for logs) into the output dict before returning to the server. The serializer currently ignores `summary`, even though it may contain `shape` and `dtype`.

**Recommendation**:

- For minimal/standard, extract dimension fields from:
  - `ref_dict.get("metadata", {})` (preferred source of truth)
  - optionally fall back to `ref_dict.get("summary", {})` if present
- Normalize `dims` output to `list[str]` consistently (the spec examples assume lists).

### 3) MEDIUM: `workflow_record` is not filtered from `outputs` in minimal/standard

**Why it matters**: The plan is explicit: workflow record should be hidden by default and only included in `full`. The current serializer does not remove `outputs["workflow_record"]`.

In practice, this means minimal/standard responses will still include a workflow record artifact entry in the outputs map (even if trimmed), which violates the spec and adds noise/tokens.

**Where**:

- `src/bioimage_mcp/api/serializers.py` iterates over all outputs and serializes them.

**Recommendation**:

- In `serialize()`, drop keys like `"workflow_record"` for `minimal`/`standard`, or drop any output that is a `NativeOutputRef` with format `workflow-record-json` unless `verbosity=="full"`.
- Add a unit test to assert workflow record is absent in minimal/standard.

### 4) MEDIUM: Full verbosity may leak `summary` and inline log `content`

**Why it matters**: The plan states:

- remove `summary` from public run responses (all verbosity levels)
- never inline log content in run responses

Current behavior in `InteractiveExecutionService.call_tool()`:

- attaches `summary` to every output
- may attach `content` to `LogRef` outputs

Current behavior in serializer:

- returns the artifact dict “as is” for `full`, which can include `summary` and `content`

This undermines the “token explosion resistance” goal for `full` and violates the explicit plan decision.

**Where**:

- `src/bioimage_mcp/api/interactive.py` adds `summary` and `content`.
- `src/bioimage_mcp/api/serializers.py` returns raw artifact dict in `full`.

**Recommendation**:

- Even in `full`, sanitize each output dict to remove at least:
  - `summary`
  - `content`
- Encourage clients to fetch log previews via `artifact_info(text_preview_bytes=...)`.

### 5) LOW: Run response key naming is inconsistent with existing API schema models

The MCP tool implementation in `src/bioimage_mcp/api/server.py` now returns `fn_id`, while `src/bioimage_mcp/api/schemas.py` still defines `RunResponse.id` and `RunRequest.id`. This may be acceptable if those schema models are not used for MCP tool I/O, but it increases confusion and future drift risk.

**Recommendation**:

- Either update/remove the unused schema models to reflect the new run response shape, or clearly document that MCP tool output is not governed by `api/schemas.py`.

## Test Coverage Gaps

The current new tests validate the serializer behavior using fixtures that do **not** resemble real outputs post-model-cleanup:

- fixtures place `shape/dims/dtype` at top level
- `dims` is set as a string (e.g., `"TCZYX"`) rather than a list
- `storage_type` uses values like `"filesystem"` rather than the store’s canonical `"file"`

These tests still pass, but may not catch the major mismatch described in Finding #2.

**Recommendations**:

1. Update serializer unit tests to build output artifacts from an actual `ArtifactRef(...).model_dump()` shape (dimension fields in `metadata`).
2. Add unit tests for:
   - workflow record filtering in minimal/standard
   - removal of `summary` and log `content` for full
   - invalid verbosity behavior (reject or coerce)
3. Add a contract test for run response verbosity shapes (the plan suggests `tests/contract/test_run_response_verbosity.py`).

## Recommended Fix Plan (Actionable)

1. **Validate verbosity**
   - Add strict validation in `server.run()` or inside `RunResponseSerializer.serialize()`.
   - Prefer a token-safe default (`minimal`) when invalid.

2. **Make minimal/standard extract dims correctly**
   - For minimal/standard, compute `shape/dims/dtype/physical_pixel_sizes/channel_names` from `metadata` (fallback `summary`).

3. **Filter workflow record from outputs by default**
   - Remove `outputs["workflow_record"]` unless `verbosity=="full"`.

4. **Strip `summary` and inline log `content` in all modes**
   - Ensure run responses never include these keys.

5. **Upgrade tests to match reality**
   - Refactor `tests/unit/api/test_run_response_serializer.py` to reflect actual artifact dict shapes.
   - Add the missing tests for spec-specific guarantees.

## Notes on Constitution / Project Constraints

- The direction (summary-first default, explicit `describe`/`artifact_info` for details) aligns with the **Anti-Context-Bloat** principle.
- The remaining gaps (workflow record hiding, log content stripping, verbosity validation) are important to maintain that constitutional compliance in practice.

---

If you want, the next step after this review would be a small follow-up patch on this branch to implement the four behavior fixes (verbosity validation, metadata-based dims extraction, workflow_record filtering, and `summary/content` stripping) plus strengthening unit/contract tests to prevent regression.
