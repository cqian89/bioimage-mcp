# Feature Specification: API Refinement & Permission System

**Feature Branch**: `008-api-refinement`  
**Created**: 2025-12-28  
**Status**: Draft  
**Input**: User description: "Fix file read/write permissions with inherit mode, consolidate tools with proper naming scheme, enhance discovery API with hierarchical navigation and multi-keyword search, rename call_tool to run_function, and guide agents to prefer activate_function workflow"

## Overview

### Terminology

- **Tool**: An MCP tool primitive registered with the server (e.g., `list_tools`, `run_function`)
- **Function**: An individual callable operation within a tool pack (e.g., `base.skimage.filters.gaussian`)
- **Tool Pack / Environment**: A collection of functions sharing a conda environment (e.g., `base`, `cellpose`)

This specification addresses four critical improvements based on the 007-workflow-test-harness validation findings and user requirements:

1. **Dynamic Permissions System (P0)**: Inherit read/write permissions from the MCP client via the Roots capability, with an "ask" pattern for existing file overwrites
2. **Tool Consolidation & Naming (P0)**: Remove the `builtin` tool pack and implement `env.package.module.function` naming scheme
3. **Hierarchical Discovery API (P1)**: Enable navigation at any level of the tool hierarchy with batch operations
4. **Enhanced Search & Agent Guidance (P2)**: Multi-keyword ranking and workflow hints to guide agents

**Why This Matters**: Current workflows fail due to permission configuration friction, overlapping tool packs causing I/O errors, and poor discoverability of the 100+ available functions. This specification provides the infrastructure needed for seamless LLM-driven bioimage analysis.

## Clarifications

### Session 2025-12-28

- Q: Should "inherit" mode be the new default? → A: Yes, with explicit logging of inherited roots at session start for auditability.
- Q: How should backward compatibility work for `call_tool`? → A: It should not; `call_tool` is removed and `run_function` is the only supported execution API.
- Q: Should we support backward compatibility aliases? → A: No. Per Constitution v0.6.0, backward compatibility is not required during early development.
- Q: Should wrapper functions like `phasor_from_flim` be removed? → A: Keep as convenience functions but also expose direct library bindings.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Seamless File Access (Priority: P0)

A scientist uses an LLM agent to analyze FLIM data. The agent already has access to their project folder. When calling bioimage-mcp tools, the system should automatically allow reading from and writing to the agent's workspace without requiring manual configuration.

**Why this priority**: This is the most common friction point. Users expect the MCP server to work within the agent's existing permissions without extra setup.

**Independent Test**: Can be tested by starting the MCP server with a client that declares Roots, then verifying read/write operations succeed within those roots without explicit allowlist configuration.

**Acceptance Scenarios**:

1. **Given** an MCP client declares `/home/user/project` as a root, **When** the server receives a read request for `/home/user/project/data/image.tif`, **Then** the read is allowed without explicit allowlist configuration
2. **Given** an MCP client declares roots, **When** the server starts a session, **Then** the inherited roots are logged for auditability
3. **Given** a tool attempts to write to a path outside all declared roots, **Then** the write is denied with a clear error message
4. **Given** a tool attempts to overwrite an existing file with `on_overwrite: ask` configured, **When** the write is requested, **Then** the system prompts for user confirmation via MCP Elicitation
5. **Given** a user denies the overwrite confirmation prompt, **When** the response is received, **Then** the write operation returns a `PermissionDenied` error with reason `user_declined`

---

### User Story 2 - Unified Tool Environment (Priority: P0)

A scientist runs a workflow that uses `gaussian_blur` followed by `phasor_from_flim`. Currently, using tools from different tool packs (`builtin` vs `base`) causes I/O errors due to different dependencies.

**Why this priority**: Cross-environment I/O failures break workflows and confuse users. Consolidating to a single tool pack eliminates this class of errors entirely.

**Independent Test**: Can be tested by running a workflow that previously failed (e.g., `builtin.gaussian_blur` → `base.phasor_from_flim`) and verifying it now succeeds with all tools in `base`.

**Acceptance Scenarios**:

1. **Given** the `builtin` tool pack is removed, **When** a user searches for `gaussian_blur`, **Then** only `base.gaussian` (or `base.skimage.filters.gaussian`) is returned
2. **Given** a workflow uses multiple image processing functions, **When** all functions run in the `base` environment, **Then** no cross-environment I/O errors occur
3. **Given** `builtin.*` functions are removed, **When** a user calls a non-existent function, **Then** the error message indicates the function is not found

---

### User Story 3 - Hierarchical Tool Discovery (Priority: P1)

An LLM agent needs to find image filtering functions. Instead of searching through 100+ functions, it can navigate the hierarchy: list environments → list packages in `base` → list modules in `skimage` → list functions in `filters`, with smart shortcuts that auto-expand single-child paths or flatten a subtree when needed.

**Why this priority**: Reduces context window usage and improves LLM decision-making by presenting structured, navigable information.

**Independent Test**: Can be tested by calling `list_tools()` with no args, then with `path="base"`, then with `path="base.skimage.filters"`, and verifying progressive hierarchy plus auto-expansion and flatten behavior.

**Acceptance Scenarios**:

1. **Given** `list_tools()` is called with no arguments, **When** the response is returned, **Then** it contains top-level environment names: `["base", "cellpose"]`
2. **Given** `list_tools(path="base")`, **When** the response is returned, **Then** it contains package/module names available in base: `["skimage", "phasorpy", "scipy", ...]`
3. **Given** `list_tools(path="base.skimage.filters")`, **When** the response is returned, **Then** it contains function names: `["gaussian", "median", "sobel", ...]`
4. **Given** `list_tools(paths=["base.skimage.filters", "base.phasorpy.phasor"])`, **When** the response is returned, **Then** it contains combined results from both paths
5. **Given** `list_tools(path="cellpose")` where cellpose has a single-child path, **When** the response is returned, **Then** it auto-expands to show functions directly with `expanded_from` field
6. **Given** `list_tools(path="base", flatten=True)`, **When** the response is returned, **Then** it contains all functions in base environment flattened

---

### User Story 4 - Multi-Keyword Search (Priority: P1)

An LLM agent searches for functions to calibrate phasors. Searching for `["phasor", "calibrate"]` should rank `base.phasor_calibrate` highest because it matches both keywords.

**Why this priority**: Current single-keyword search returns too many results. Multi-keyword search with ranking helps agents find the right function faster.

**Independent Test**: Can be tested by calling `search_functions(keywords=["phasor", "calibrate"])` and verifying `phasor_calibrate` is ranked first.

**Acceptance Scenarios**:

1. **Given** a search with keywords `["phasor", "calibrate"]`, **When** results are returned, **Then** functions matching both keywords rank higher than those matching only one
2. **Given** a search with keywords `["gaussian", "filter"]`, **When** results are returned, **Then** `base.gaussian` ranks high due to matching both in name/description
3. **Given** a search with `limit=5`, **When** more than 5 functions match, **Then** only the top 5 ranked functions are returned
4. **Given** a function matches a keyword in its name vs another matching only in tags, **When** results are ranked, **Then** the name match ranks higher (weight 3 vs weight 1)
5. **Given** a search with typo `"gausian"`, **When** results are returned, **Then** `base.gaussian` is still found (typo tolerance via n-gram tokenization)

---

### User Story 5 - Batch Function Descriptions (Priority: P2)

An LLM agent needs to understand the parameters of multiple functions before deciding which to use. Instead of making 5 separate `describe_function` calls, it can request all 5 schemas in one call.

**Why this priority**: Reduces round-trips and improves agent efficiency, but single-function describe still works fine.

**Independent Test**: Can be tested by calling `describe_function(fn_ids=["base.gaussian", "base.median", "base.sobel"])` and verifying all three schemas are returned.

**Acceptance Scenarios**:

1. **Given** `describe_function(fn_ids=["base.gaussian", "base.median"])`, **When** the response is returned, **Then** it contains schemas for both functions
2. **Given** one fn_id in the list doesn't exist, **When** the response is returned, **Then** valid functions return schemas and the missing function returns an error entry
3. **Given** backward compatibility, **When** `describe_function(fn_id="base.gaussian")` is called (single string), **Then** it still works as before

---

### User Story 6 - Guided Activation Workflow (Priority: P2)

LLM agents often call `run_function` directly without first activating functions. The system should provide hints encouraging the proper workflow: search → activate → describe → run.

**Why this priority**: Improves agent behavior over time but doesn't block core functionality.

**Independent Test**: Can be tested by calling `run_function` on a non-activated function and verifying the response includes a `workflow_hint`.

**Acceptance Scenarios**:

1. **Given** a function is executed via `run_function` without prior activation, **When** the response is returned, **Then** it includes `workflow_hint: "TIP: Use activate_functions before run_function for better guidance"`
2. **Given** `agent_guidance.warn_unactivated: true` in config, **When** a non-activated function is run, **Then** the response includes a `warnings` array with the guidance message
3. **Given** a function was previously activated via `activate_functions`, **When** it is run via `run_function`, **Then** no warning is included

---

### User Story 7 - Function Naming (Priority: Cancelled)

Functions use canonical `env.package.module.function` naming. Short names and aliases are NOT supported.

**Why this priority**: No migration is needed if the system starts with canonical names only.

**Independent Test**: N/A - Story cancelled; canonical naming is the only supported mode.

**Acceptance Scenarios**: N/A - Story cancelled. The following scenarios are retained for historical reference only and will NOT be implemented:

1. ~~**Given** a function is registered with canonical name `base.skimage.filters.gaussian`, **When** `list_tools(path="base.skimage.filters")` is called, **Then** only canonical names are shown~~
2. ~~**Given** a short name like `base.gaussian`, **When** a user calls the function, **Then** the error message indicates the function is not found~~

---

### Edge Cases

- **Roots capability not supported by client**:
  - What happens: Client doesn't declare any roots
  - Expected: Fall back to explicit allowlist configuration; log warning about missing roots (see FR-005)

- **Empty roots list from client**:
  - What happens: Client declares Roots capability but returns empty list
  - Expected: All file operations denied; log error suggesting configuration

- **Elicitation not supported by client**:
  - What happens: Server tries to prompt for overwrite confirmation but client doesn't support Elicitation
  - Expected: Fall back to `on_overwrite` default behavior (allow or deny based on config)

- **Search with zero keywords**:
  - What happens: `search_functions(keywords=[])` is called
  - Expected: Return error "At least one keyword required"

- **list_tools with invalid path**:
  - What happens: `list_tools(path="nonexistent.package")` is called
  - Expected: Return empty list with no error (path may not have children)

- **Deep single-child path**:
  - What happens: `cellpose.cellpose.models` has only one level with children
  - Expected: Auto-expand traverses entire single-child chain, returning functions

- **Flatten with pagination**:
  - What happens: `list_tools(path="base", flatten=True)` returns 47 functions
  - Expected: Respects `limit` parameter and returns `next_cursor` for pagination

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*

#### 1. Stable MCP Surface (Anti-Context-Bloat)

**Impact**: Minor expansion of API parameters (batch support, hierarchical paths).

**Compliance**:
- `list_tools` and `describe_function` responses remain paginated
- New parameters are additive (backward compatible)
- Full schemas still fetched only via `describe_function`, not in listings
- `run_function` is the only supported execution API

#### 2. Isolated Tool Execution

**Impact**: Removal of `builtin` simplifies to single base environment for most operations.

**Compliance**:
- All tools continue to run in `bioimage-mcp-base` or `bioimage-mcp-cellpose` environments
- No changes to subprocess isolation model
- Cross-environment I/O errors eliminated by consolidation

#### 3. Artifact References Only

**Impact**: No changes to artifact model.

**Compliance**:
- All inputs/outputs remain typed artifact references
- No embedding of arrays in MCP messages

#### 4. Reproducibility & Provenance

**Impact**: Permission decisions must be logged for auditability.

**Compliance**:
- Inherited roots logged at session start
- Permission allow/deny decisions logged with path and reason
- All other provenance recording unchanged

#### 5. Safety & Observability (AMENDED in Constitution v0.5.0)

**Impact**: Permission system now supports "inherit" mode per constitution amendment.

**Compliance**:
- MCP Roots capability used for inherited permissions
- Inherited roots logged at session start for auditability
- Write operations to existing files prompt via MCP Elicitation when configured
- All permission decisions logged

#### 6. Test-Driven Development

**Impact**: All new functionality requires tests-first.

**Compliance**:
- Permission inheritance tests written before implementation
- Hierarchical list_tools tests written before implementation
- Multi-keyword search tests written before implementation
- Call dispatch error handling tests written before implementation

### Functional Requirements

#### Permissions System

- **FR-001**: System MUST support `permissions.mode` configuration with values: `explicit`, `inherit`, `hybrid`
- **FR-002**: When `mode: inherit`, system MUST call MCP `list_roots()` to obtain allowed paths from client
- **FR-003**: Inherited roots MUST be logged at session start with full path list
- **FR-004**: When `permissions.on_overwrite: ask`, system MUST prompt user via MCP Elicitation before overwriting existing files
- **FR-005**: If client doesn't support Roots capability, system MUST fall back to explicit allowlists with logged warning
- **FR-006**: All permission decisions (allow/deny/ask) MUST be logged with path, action, and reason

#### Tool Consolidation

- **FR-007**: System MUST remove the `builtin` tool pack from the default tool manifest roots
- **FR-008**: System MUST provide migration guidance for users referencing `builtin.*` functions in a dedicated "Migration from builtin" section of the README
- **FR-009**: All image processing functions MUST run in the `bioimage-mcp-base` environment
- **FR-010**: System SHOULD expose direct library function bindings with full naming (e.g., `base.skimage.filters.gaussian`)

#### Hierarchical Discovery

- **FR-011**: `list_tools()` with no arguments MUST return top-level environment names
- **FR-012**: `list_tools(path="env")` MUST return package/module names one level below
- **FR-013**: `list_tools(path="env.package.module")` MUST return function names at that level
- **FR-014**: `list_tools(paths=[...])` MUST support multiple paths in a single call
- **FR-015**: Hierarchical listing MUST respect existing pagination (limit/cursor)
- **FR-032**: `list_tools` MUST auto-expand paths with single children until reaching functions or multiple children
- **FR-033**: `list_tools` response MUST include `expanded_from: string | null` field when auto-expansion occurred (contains the original path before expansion, null if no expansion)
- **FR-034**: `list_tools` MUST accept optional `flatten: bool` parameter to return all functions under a path. When `flatten=True`, auto-expansion is skipped and all descendant functions are returned directly.

#### Multi-Keyword Search

- **FR-016**: `search_functions` MUST accept `keywords: list[str] | str` parameter
- **FR-017**: Results MUST be ranked by: (1) number of keywords matched, (2) total weighted matches using BM25-style scoring with n-gram tokenization for typo tolerance
- **FR-018**: Match weights MUST be: name=3, description=2, tags=1
- **FR-019**: `search_functions` MUST support pagination via `limit` (default 20) and `cursor` parameters

#### Batch Operations

- **FR-020**: `describe_function` MUST accept `fn_ids: list[str]` for batch descriptions
- **FR-021**: Batch describe MUST return a dict containing `schemas` and `errors` mappings
- **FR-022**: Single fn_id parameter MUST remain backward compatible

#### API Naming

- **FR-023**: System MUST register `run_function` as the canonical name for function execution
- **FR-024**: `call_tool` is removed; `run_function` is the only supported execution API

#### Agent Guidance

- **FR-025**: System SHOULD log when a function is executed without prior activation for observability
- **FR-026**: Responses SHOULD include `workflow_hint` field for guidance
- **FR-027**: When `agent_guidance.warn_unactivated: true`, non-activated function calls MUST include warning
- **FR-028**: Warning message MUST suggest using `activate_functions` before `run_function`

#### Function Naming

- **FR-029**: Functions MUST use canonical `env.package.module.function` naming only; short names and aliases are NOT supported

### Key Entities

#### PermissionMode
Enumeration of permission configuration modes.

**Values**:
- `explicit`: Use only explicitly configured allowlists (current behavior)
- `inherit`: Inherit allowed paths from MCP client via Roots capability
- `hybrid`: Combine inherited roots with additional explicit paths

#### WritePermission
Result of write permission check.

**Values**:
- `ALLOWED`: Write permitted without confirmation
- `DENIED`: Write not permitted
- `ASK`: Prompt user for confirmation via Elicitation

#### OverwritePolicy
Configuration for handling writes to existing files.

**Values**:
- `allow`: Overwrite without prompting
- `deny`: Reject overwrite attempts
- `ask`: Prompt user via MCP Elicitation (requires client support)

#### PermissionDecision
Structured record of a permission check result for audit logging.

**Fields**:
- `path: string` - The file path that was checked
- `action: "read" | "write"` - The requested operation
- `result: WritePermission` - The decision (ALLOWED/DENIED/ASK)
- `reason: string` - Human-readable explanation (e.g., "path within inherited root /home/user/project")
- `timestamp: datetime` - When the decision was made

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: MCP server starts and inherits roots from client without explicit allowlist configuration
  - Measurement: Integration test with mock client declaring Roots succeeds
  - Verification: Read/write operations within roots succeed; outside roots fail

- **SC-002**: All tools run in unified `base` environment without cross-environment I/O errors
  - Measurement: Validation workflow from 007 spec completes without the 4 failures
  - Verification: `base.gaussian` → `base.phasor_from_flim` pipeline succeeds

- **SC-003**: Hierarchical `list_tools` enables navigation at any level
  - Measurement: `list_tools()` returns envs, `list_tools(path="base")` returns packages
  - Verification: Integration test validates 3-level hierarchy navigation

- **SC-004**: Multi-keyword search ranks functions by match quality
  - Measurement: Search `["phasor", "calibrate"]` returns `phasor_calibrate` as top result
  - Verification: Unit test validates ranking algorithm

- **SC-005**: Batch `describe_function` reduces round-trips
  - Measurement: Single call retrieves 5 function schemas
  - Verification: Integration test validates batch response structure

- **SC-006**: Agent guidance hints included in responses
  - Measurement: Non-activated function call includes `workflow_hint`
  - Verification: Integration test validates hint presence

### Acceptance Criteria

**For Permissions System:**
- [ ] `permissions.mode: inherit` is the new default in config schema
- [ ] MCP Roots capability integration implemented and tested
- [ ] Elicitation prompt for overwrite confirmation works with supporting clients
- [ ] Fallback to explicit allowlists when Roots not available
- [ ] All permission decisions logged with path, action, reason

**For Tool Consolidation:**
- [ ] `tools/builtin/` directory removed from repository
- [ ] Migration guide created for `builtin.*` function users
- [ ] All base toolkit functions tested in single environment

**For Hierarchical Discovery:**
- [ ] `list_tools()` returns environment names
- [ ] `list_tools(path=...)` navigates hierarchy
- [ ] `list_tools(paths=[...])` supports batch queries
- [ ] Pagination works at all hierarchy levels

**For Multi-Keyword Search:**
- [ ] `keywords` parameter accepts list or string
- [ ] Ranking algorithm implemented (keyword count, weighted matches)
- [ ] Default limit of 20 results
- [ ] Unit tests cover edge cases (empty keywords, no matches)

**For Batch Operations:**
- [ ] `describe_function(fn_ids=[...])` returns dict of schemas
- [ ] Error handling for missing functions in batch
- [ ] Backward compatibility with single fn_id

**For API Naming:**
- [ ] `run_function` registered as primary handler
- [ ] `call_tool` removed from API surface

**For Agent Guidance:**
- [ ] `workflow_hint` field in responses
- [ ] `warn_unactivated` config option implemented
- [ ] Warning only shown for non-activated functions

### Quality Gates

Before merging this feature:

1. **Test Coverage**: ≥80% branch coverage for new permission logic in `api/permissions.py` and `config/fs_policy.py`
2. **Performance**: Hierarchical `list_tools` completes in <100ms for any single path query with default limit (excludes network latency)
3. **Documentation**: README updated with new permission modes
4. **Contract Tests**: Schema validation for all new/modified API responses
5. **Integration Tests**: Full workflow test passes with inherit mode
6. **Migration Guide**: Documentation for `builtin` tool pack removal

## Future Considerations

### Potential Enhancements

1. **Permission caching**: Cache inherited roots with TTL to reduce Roots calls
2. **Glob patterns in paths**: `list_tools(path="base.skimage.*")` for wildcard navigation
3. **Function favorites**: Track frequently used functions per session for recommendations

### Integration Opportunities

1. **IDE integrations**: Expose hierarchical structure for IDE tool panels
2. **Documentation generation**: Auto-generate docs from hierarchical structure
3. **Workflow templates**: Pre-defined function sequences for common analysis patterns

## Migration & Compatibility

Breaking changes are expected per Constitution v0.6.0, with no deprecation period. This release removes:

- `call_tool` (use `run_function` only)
- `builtin.*` functions (use `base.*` canonical names)
- Short names and aliases (use canonical `env.package.module.function` naming)

## References

### Related Specifications
- [Spec 007: Workflow Test Harness](../007-workflow-test-harness/spec.md) - Validation findings that drove this spec
- [Spec 006: Phasor Usability Fixes](../006-phasor-usability-fixes/spec.md) - FLIM analysis functions affected by consolidation

### External Documentation
- [MCP Specification](https://spec.modelcontextprotocol.io/) - Roots capability and Elicitation
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - Implementation reference

### Test Data Sources
- [Validation Report](../../datasets/FLUTE_FLIM_data_tif/outputs/20251228_0116_test_validation_workflow.md) - Issues that drove this spec

---

**Next Steps After Approval**:
1. Create feature branch `008-api-refinement`
2. Write contract tests for permission inheritance (TDD red phase)
3. Remove `tools/builtin/` directory
4. Implement MCP Roots integration
5. Implement hierarchical `list_tools`
6. Implement multi-keyword search ranking
7. Register `run_function` as the only execution API
8. Run full validation workflow and verify all issues resolved
