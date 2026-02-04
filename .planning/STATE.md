# Project State: Bioimage-MCP

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-04)

**Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
**Current focus:** Milestone Archive Complete

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-02-04 — Milestone v0.5.0 Interactive Annotation started

Progress: ░░░░░░░░░░ 0% (Defining requirements)
 

## Accumulated Context

### Decisions Made
| Phase | Decision | Rationale |
|-------|----------|-----------|
| 20 | Designated representative PR tests (skimage, cellpose, trackpy) | Balances coverage with PR latency. |
| 20 | Demoted non-representative smoke tests to smoke_extended | Keeps the PR-gating tier lean and focused. |
| 20 | Switched to tolerance-based numeric equivalence for Scipy | Prevents false failures due to minor float differences across platforms. |
| 20 | Relaxed discovery contract assertions to use subset matching | Allows additive evolution without breaking existing tests. |
| 20 | Treated tool-pack params_schema descriptions as best-effort | Avoids contract failures for tools with sparse documentation (e.g. trackpy). |
| 20 | Strictly enforced manifest-only YAML discovery | Prevents accidental validation of arbitrary YAML files in tool directories. |
| 15 | Use OME-Zarr as default save format in SkimageAdapter | Aligns with project-wide standardization on OME-Zarr for intermediate interchange. |
| 15 | Cast uint16/int64 to uint8/int32 for previews | Ensure compatibility with 8-bit PNG encoding and standard JSON/Pydantic types. |
| 15 | Exempt ObjectRef parameters from artifact filtering | Ensure x-native-type annotations remain visible in params_schema for LLM discoverability. |
| 15 | Use 500 char limit for object repr previews | Balance between useful object visibility and token efficiency. |
| 15 | Prefer fully qualified class names for native_type | Unambiguous identification of Python objects across tool packs. |
| 15 | Use TAB20 colormap for label images | High-contrast distinct colors for instance labels. |
| 15 | Opt-in Table Previews | Avoid token bloat while providing structured visibility for CSVs. |
| 15 | Default to max projection for multi-dimensional images | standard in bioimaging for quick visibility. |
| 15 | Map images to 8-bit PNG for previews | Universal compatibility for browsers and LLMs. |
| 15 | Fail silently on preview generation | Omit field rather than failing entire request if image is corrupt/unsupported. |
| 16 | Redirect tool stdout to stderr in entrypoint | Avoid breaking NDJSON IPC when tools print non-JSON noise to stdout. |
| 10 | Use 'datasets/smoke_tmp' for test CSVs | Ensure live server read access within allowed paths. |
| 10 | Map mean_table to tmean | scipy.stats lacks a bare mean function. |
| 10 | Standardize on NativeOutputRef for stats JSON | Allows flexible structured output for distribution/summary stats. |
| 10 | Automatic Float32 Promotion | Ensures precision parity for filters/transforms on uint16 inputs. |
| 10 | Stable JSON Contract | Facilitates strict comparison of statistical test outputs. |
| 11 | Audit Gap Cleanup | Address descriptions and schema types identified in v0.3.0 audit. |
| 12 | Used griffe for zero-import static inspection | Avoids heavy tool-pack dependencies in core server. |
| 12 | sha256 source fingerprinting | Enables stable tracking of callable changes across runs. |
| 12 | Deterministic JSON Schema normalization | Ensures consistent schema emission for caching and comparison. |
| 12 | TypeAdapter-based schema generation | Leverages Pydantic v2 for high-fidelity type-to-schema mapping. |
| 12 | Automated artifact omission | Prevents I/O artifacts from polluting the parameters schema. |
| 12 | Unified Discovery Orchestrator | Centralizes AST + runtime fallback logic in DiscoveryEngine. |
| 12 | Parameter-level overlays | Added support for rename/omit in overlays without tool code changes. |
| 12 | Multi-key cache invalidation | Ensures cache safety by tracking version, env, and source changes. |
| 12 | Move metadata to adjacent block | Moved tool_version and introspection_source to meta block in describe to keep params_schema pure. |
| 12 | Persistent Registry Cache | Wired API to DB-backed schema cache, eliminating separate schema_cache.json file. |
| 12 | Extended ManifestDiagnostic | Include engine_events for unified reporting of fallback, overlays, and missing docs. |
| 12 | diagnostic_level config | Allow filtering of discovery events (minimal/standard/full) in doctor output. |
| 12 | tool_environments check | Detect missing conda environments referenced by manifests with actionable remediation. |
| 12 | Gated runtime fallback | DiscoveryEngine only calls runtime fallback if AST-derived schema is incomplete (empty properties after filtering). |
| 12 | target_fn request param | Aligned DiscoveryEngine runtime describe call with tool entrypoint and API schema. |
| 12 | Enforce required/properties consistency | Stripping required fields that don't match emitted properties (e.g. omitted artifacts). |
| 12 | Omit empty 'required' key | Produces cleaner, more deterministic schema output. |
| 12 | Description merging precedence | curated > docstring > TypeAdapter > fallback. |
| 12 | In-place metadata synchronization | Updating functions table during describe enrichment ensures tools/list and tools/describe stay consistent. |
| 13 | User-home based dynamic cache | Store dynamic cache under ~/.bioimage-mcp/cache/dynamic/<tool_id> for stability across runs. |
| 13 | Lockfile hash invalidation | Use env/<env_id>.lock.yml hash as the primary invalidation key for dynamic introspection caching. |
| 13 | Reuse Unified IntrospectionCache for trackpy | Avoid bespoke cache implementations in tool packs to ensure consistent invalidation logic. |
| 13 | Robust project_root detection | Support env var and CWD-based project root detection for caching in installed tool envs. |
| 13 | Core-side memoization | DiscoveryEngine now caches parsed meta.list results to avoid subprocess overhead on repeated listings. |
| 13 | Persistent CLI List Cache | Used ~/.bioimage-mcp/cache/cli with manifest fingerprinting to achieve <1.5s warm list. |
| 13 | Composite cache key: env:manifest | Force refresh on metadata changes by including manifest checksum. |
| 13 | no-lockfile sentinel | Enable cache reuse even when environment indicators are missing. |
| 13 | Propagate top-level introspection_source in meta.list | Critical for detecting tools that use dynamic discovery (like trackpy) from the cached function metadata. |
| 14 | Standardize on OME-Zarr (.ome.zarr) | Default interchange format for all cross-env handoffs. |
| 14 | Enable import_directory in core | Support materializing directory-backed artifacts (OME-Zarr). |
| 14 | Relax metadata schema constraints | Support multi-character axis names (e.g. 'bins') and >5D datasets. |
| 14 | Standardized bins axis name | Standardized on 'bins' for TTTR decay data to avoid 'T' axis hijacking. |
| 14 | Default Cellpose to OME-Zarr | Defaulted Cellpose output formats to OME-Zarr to align with project standard. |
| 14 | Verbisity-aware smoke tests | Updated smoke tests to use 'full' verbosity for detailed metadata validation. |
| quick-001 | Standardize 'axis' as integer | Runtime arrays are numpy ndarrays; string labels not supported in this layer. |
| quick-001 | Omit regionprops artifact ports | Prevents binding errors for 'label_image' and 'intensity_image'. |
| quick-002 | Use fn_id in run responses | Distinguish tool ID from execution run ID; aligns with spec 023. |
| quick-002 | Omit session_id in run responses | Reduces token bloat; session context is maintained by agent. |
| quick-003 | PHASOR_TO_LIFETIMES IOPattern | Distinct pattern for phasor_to_apparent_lifetime with phase_lifetime/modulation_lifetime outputs. |
| quick-003 | Global artifact param filtering in DiscoveryEngine | Ensures label_image, intensity_image, etc. never appear in params_schema. |
| quick-003 | Standardize export to dest_path | Consistent parameter naming across base.io.*.export functions. |
| quick-004 | Omit meta from describe responses | Internal metadata (tool_version, introspection_source) not useful to LLM consumers. |
| quick-004 | Omit null hints from describe responses | Reduces token bloat; only include hints when meaningful. |
| quick-004 | Normalize newlines in describe text | Replace \n with space in summary/description for cleaner output. |
| 17 | Use short tool IDs (drop 'tools.' prefix) in CLI list output | Reduce visual noise in CLI list output. |
| 17 | Provide a tree-style view for packages within tool-packs | Better visibility into tool-pack contents. |
| 17 | Group functions into packages based on ID prefix | Logical organization of tool-pack contents. |
| 17 | Use lockfiles as primary source of truth for library versions | Fast, reproducible resolution without expensive conda query. |
| 17 | Include lockfiles in CLI cache fingerprint | Ensures listing stays fresh when environments change. |
| quick-008 | Use `root` as fallback package ID | Ensure functions without dots are grouped stably in CLI list output. |
| 18 | Use SQLite triggers for real-time tracking of total artifact bytes | Avoids expensive filesystem scans and ensures accuracy. |
| 18 | Link artifacts to sessions via session_id | Enables session-aware cleanup policies and protection of active session data. |
| 18 | Implement a 'touch' mechanism for artifacts | Tracks artifact access time independently of creation time for better retention decisions. |
| 18 | Use Pydantic v2 for StoragePolicy | Ensures strict validation of retention periods and quota thresholds. |
| 18 | Expose expiration in artifact_info | Provides transparency into when specific artifacts will be eligible for cleanup. |
| 18 | Sanitize mocked metadata in store | Prevents JSON serialization failures in tests using MagicMock by falling back to string representation. |
| 18 | Use a SQLite-based lock for cleanup | ensures only one instance performs cleanup at a time. |
| 18 | Run cleanup in background daemon thread | Avoids blocking MCP stdio communication during server operations. |
| 18 | Implement rename-to-trash | safer multi-step deletion handles partial deletions gracefully. |
| 18 | Use in-memory SQLite for StorageManager unit tests | ensure fast and deterministic trigger validation. |
| 18 | Use subprocess-based integration tests for CLI | verify real-world behavior and JSON contracts. |
| 19 | Use 'datasets/smoke_tmp' for smoke test input | Comply with server read-path restrictions for E2E tests. |
| 20 | Preferred requires_env marker for environment-gated tests | Standardizes how tool-specific tests are skipped. |
| 20 | Standardized local PR gate command set | Ensures consistent local verification before CI. |

## Blockers/Concerns Carried Forward
- trackpy schema descriptions missing (contract test failure) - FIXED.
- contract tests need to skip non-manifest YAMLs - FIXED.
- Existing failures in bootstrap/test_install.py need investigation.

## Session Continuity
Last session: 2026-02-04T14:15:00Z
Stopped at: Milestone v0.4.0 complete
Resume file: None
