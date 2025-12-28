<!--
Sync Impact Report
- Version change: 0.4.0 -> 0.5.0
- Principles updated: Principle V (Safety, Testing, and Observability)
- Added sections: Tool Naming convention in Architecture Constraints
- Removed sections: None
- Templates requiring updates: None
- Follow-up TODOs: Update config.yaml documentation for permissions.mode
-->

# Bioimage-MCP Constitution

## Core Principles

### I. Stable MCP Surface (Anti-Context-Bloat)
Bioimage-MCP MUST keep the LLM-facing MCP interface stable and compact.

Non-negotiables:
- MCP discovery responses MUST be paginated and default to summaries.
- Full schemas MUST be fetched only on-demand (e.g., via `describe_function(fn_id)`).
- Tool calls and workflow execution MUST return IDs and artifact references, not large
  in-message payloads.
- Changes that expand the MCP surface area MUST come with a migration plan and version
  bump justification.

Rationale: Tool catalogs grow quickly in bioimage analysis; the interface must scale
without forcing prompt/context growth.

### II. Isolated Tool Execution (Per-Tool Conda Envs)
Each analysis tool MUST run in its own isolated environment, invoked via a strict
execution boundary.

Non-negotiables:
- Tools MUST execute in their own conda/micromamba environment (e.g., `bioimage-mcp-*`).
- The core server MUST treat tool processes as fallible and isolate crashes via
  subprocess boundaries.
- Tool integration MUST be declarative (manifest + shim) rather than bespoke in-core
  glue.
- Heavy or fragile stacks (PyTorch, TensorFlow, Java/Fiji) MUST NOT be installed into
  the core server environment.

Rationale: Dependency conflicts are the norm across imaging stacks; isolation keeps the
core server reliable and reduces install/debug churn.

### III. Artifact References Only (Typed I/O)
All inter-tool data exchange MUST use typed artifact references.

Non-negotiables:
- Tool inputs/outputs MUST be passed by reference (URI + metadata), never by embedding
  arrays/binaries in MCP messages.
- Artifacts MAY be backed by files (OME-TIFF/OME-Zarr) or managed session memory (for 
  performance), provided they are addressable via a stable Reference URI.
- Intermediate image artifacts SHOULD use OME-Zarr (OME-NGFF) by default; OME-TIFF MAY
  be supported for compatibility.
- Artifact references MUST carry enough metadata to validate I/O compatibility
  (axes, pixel sizes, channels, checksums, etc.).
- Artifact formats and reference schemas MUST be stable and versioned.

Rationale: Reference-based I/O enables scale (large volumes), allows replay/debugging,
and prevents protocol-level context bloat. Memory-backed options reduce latency for 
iterative workflows.

### IV. Reproducibility & Provenance (Record + Replay)
The system MUST make analysis runs reproducible and auditable.

Non-negotiables:
- Environments MUST be pinned (e.g., via `conda-lock`) and installable reproducibly.
- Workflow execution MUST record a linear plan (steps, params, tool versions, lockfile
  hashes, timestamps).
- The system MUST be able to re-run recorded workflows (`replay_workflow`) against the
  same inputs.
- Outputs MUST include provenance links to their upstream inputs and parameters.

Rationale: Scientific workflows require traceability and repeatability to be trusted.

### V. Safety, Testing, and Observability
Bioimage-MCP MUST be safe-by-default and easy to debug.

Non-negotiables:
- Tool code runs with user privileges; this MUST be documented clearly.
- Subprocess boundaries provide fault isolation (crash containment), NOT security
  sandboxing.
- File and network access policies MUST be explicit and verifiable through one of:
  a) Explicit allowlists in configuration (current behavior)
  b) MCP Roots capability with session-start logging of inherited roots
  c) Hybrid mode combining both with explicit additions
- Write operations to existing files SHOULD prompt for user confirmation via MCP 
  Elicitation when `on_overwrite: ask` is configured.
- All permission decisions (allow/deny/ask) MUST be logged with path and reason.
- Runs MUST emit structured logs and persist them as artifacts.
- Changes to core workflow execution, artifact schemas, or tool shims MUST include
  automated tests.

Rationale: Local-first tools still execute arbitrary code; safety, logging, and tests
are the minimum bar for user trust and maintainability.

### VI. Test-Driven Development (Red-Green-Refactor)

All implementation work MUST follow the TDD cycle.

Non-negotiables:
- **Red**: Write a failing test that captures the expected behavior BEFORE writing
  implementation code.
- **Green**: Write the minimum implementation code required to make the test pass.
- **Refactor**: Improve code structure while keeping tests green.
- Each task in `tasks.md` MUST have its tests written and failing BEFORE the
  implementation work begins.
- PRs that add functionality without accompanying tests (written first) MUST be rejected.

Rationale: TDD ensures robust, regression-resistant code and forces clear thinking about
interfaces and edge cases before implementation.

## Architecture Constraints

- **MCP SDK**: Use the official MCP Python SDK for server transports and protocol
  maintenance.
- **Tool packaging**: Tools are discovered from on-disk manifests and executed via
  per-tool shims (`describe()` and `run(fn_id, inputs, params)`).
- **Storage**: Prefer local filesystem artifacts with SQLite index for MVP; Postgres
  and S3/MinIO in upgrade path.
- **Performance**: Prefer `conda-lock` + `micromamba` for fast, reproducible installs.
- **Viewer integration**: napari is optional; headless workflows are the default.
- **Python version**: Core server uses Python 3.13; tool envs MAY pin their own
  Python version per project requirements.
- **Env naming**: Use `bioimage-mcp-*` prefix for all environments to avoid conflicts
  with user envs.
- **Platform support**: Cross-platform (Linux, macOS, Windows) from the start; document
  platform-specific behavior where it differs (e.g., Java/Fiji, ML wheel availability).
- **Artifact types**: Canonical types are `BioImageRef`, `LabelImageRef`, `TableRef`,
  `ModelRef`, and `LogRef` (defined in Architecture document).
- **Bootstrap CLI**: `bioimage-mcp install`, `doctor`, `configure`, and `serve` commands
  provide installation and runtime lifecycle (defined in PRD §6.6).
- **Reference implementation**: `MicroscopyLM` (`../MicroscopyLM/`) provides reference
  patterns for registry, env manager, and subprocess executors.
- **Tool naming**: Functions SHOULD use `env.package.module.function` naming scheme
  (e.g., `base.skimage.filters.gaussian`) for clarity and discoverability. Legacy
  short names (e.g., `base.gaussian`) MAY be supported as aliases during migration.
- **API naming**: `run_function` is the canonical name for function execution; 
  `call_tool` is deprecated but MAY be supported as an alias for backward compatibility.

## Development Workflow & Quality Gates

- **Reviews**: Every PR MUST include a brief "Constitution Check" confirming which
  principles apply and how they are satisfied.
- **Versioning**: Breaking changes to public contracts (MCP API, artifact schemas,
  manifest fields) MUST be versioned and accompanied by migration notes.
- **Quality**: Prefer `ruff` for formatting/linting and `pytest` for tests; target
  meaningful coverage on core execution paths.
- **Reproducibility**: Changes that affect execution environments MUST update lockfiles
  and provenance recording.

## Governance

This constitution defines non-negotiable project rules and supersedes lower-level
guidance when conflicts exist.

Amendment procedure:
- Amendments MUST be made via PR that updates `.specify/memory/constitution.md`.
- The PR MUST include a Sync Impact Report update (templates/docs touched) and a
  semver bump rationale.
- If an amendment introduces breaking governance or removes/redefines a principle,
  it MUST be a MAJOR bump.

Versioning policy (semver):
- **MAJOR**: Backward-incompatible governance changes; principle removals or
  redefinitions.
- **MINOR**: New principles or materially expanded guidance.
- **PATCH**: Clarifications, wording refinements, typo fixes.

Compliance expectations:
- Feature plans MUST include an explicit constitution gate section.
- Exceptions MUST be documented in the plan with rationale and mitigation, and MUST
  be approved in review.

**Version**: 0.5.0 | **Ratified**: 2025-12-26 | **Last Amended**: 2025-12-28
