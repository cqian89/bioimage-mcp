# Feature Specification: Cellpose Object-Oriented API & Stateful Execution

**Feature Branch**: `017-cellpose-api`  
**Created**: 2026-01-06  
**Status**: Draft  
**Input**: User description: "Enable stateful Cellpose execution by supporting ObjectRef for model persistence and class-based method calling for more natural integration of the Cellpose Python API."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fast Iterative Segmentation (Priority: P1)
As a researcher, I want to load a large Cellpose model once and use it to segment multiple images without the overhead of reloading the model weights into memory/VRAM for every single image.
**Why this priority**: High-throughput analysis is currently throttled by cold-start model loading times (often 5-10 seconds per call), making interactive loops or large dataset processing inefficient.
**Independent Test**: Use the `bioimage-mcp_run` tool to call a model loader, receive an `ObjectRef`, and then call `eval` twice using that same `ObjectRef`. Compare total time against two standard "cold" calls.
**Acceptance Scenarios**:
1. **Given** a Cellpose model is successfully instantiated as an `ObjectRef`, **When** the `eval` function is called with that `ObjectRef`, **Then** the segmentation completes at least 2x faster (SC-003) than a call that must load the model from disk.

### User Story 2 - Model Fine-Tuning Workflow (Priority: P2)
As a data scientist, I want to train a Cellpose model on my specific data, get a reference to the resulting weights, and immediately use those weights to create a new model instance for validation.
**Why this priority**: Supports the complete lifecycle of image analysis from training/fine-tuning to inference within a single reproducible workflow.
**Independent Test**: Execute a `train_seg` tool call, verify it returns a `NativeOutputRef` (weights) and `TableRef` (losses), then pass that weight reference to a model instantiation tool.
**Acceptance Scenarios**:
1. **Given** a set of training images and labels, **When** `train_seg` is executed, **Then** a reference to the new model weights is returned which can be passed to subsequent model creation steps.

### Edge Cases
- **Resolution Precedence**: When an `ObjectRef` is used as input, the runtime MUST resolve it using the following deterministic order:
    1. **In-process cache**: Check if the object is already live in the current tool process memory.
    2. **Artifact load**: Attempt to deserialize from the `uri` (pickle file).
    3. **Reconstruction**: If loading fails, attempt to re-instantiate using recorded `init_params`.
- **VRAM Eviction**: If an `ObjectRef` is evicted from the active tool process cache due to resource limits, the system MUST fallback to the resolution precedence (artifact load or reconstruction).
- **Serialization Failures**: If a specific Python object cannot be safely pickled (e.g., it holds open file handles or network sockets), the system must fail gracefully during the artifact creation stage.
- **Hardware Mismatch**: If an `ObjectRef` was created on a system with a GPU but is replayed on a CPU-only system, the runtime SHOULD attempt a `map_location='cpu'` load during artifact load. If it fails, it MUST return a structured error with a hint to use `device='cpu'`.
- **Artifact Deletion**: If the underlying pickle file for an `ObjectRef` is deleted and reconstruction is impossible, subsequent calls MUST return a structured `ArtifactNotFoundError` (FR-009).

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*
- **Isolation**: Tool processes must remain isolated subprocesses. `ObjectRef` data must be serialized/deserialized across the subprocess boundary.
- **Artifact I/O**: `ObjectRef` is a first-class `ArtifactRef` type, ensuring consistency with images and tables.
- **Discovery**: The Registry must filter out methods using `**kwargs` unless an explicit schema overlay is provided to ensure safe AI interaction.
- **Reproducibility**: Workflow exports must include enough metadata to reconstruct an `ObjectRef` (class name, initialization parameters) in a new session.

### Functional Requirements
- **FR-001**: The registry MUST provide schema support for targeting specific Python classes as tool sources, enabling the definition of class-level metadata and constraints.
- **FR-002**: The tool runtime MUST handle `ObjectRef` by deserializing the object before calling the requested method.
- **FR-003**: The `describe` tool MUST correctly show `ObjectRef` as a valid input/output type for relevant functions.
- **FR-004**: The system MUST support `ObjectRef` in workflow export and `session_replay`.
- **FR-005**: The discovery engine MUST support automated introspection of class `__init__` and public methods to extract signatures and generate MCP tool definitions.
- **FR-006**: The runtime MUST correctly split user-provided parameters into `init_params` (for the class constructor) and method parameters.
- **FR-007**: `ObjectRef` instances MUST be persisted across steps within the same session via a local process cache to maximize performance.
- **FR-008**: The runtime MUST manage system memory/VRAM via an eviction policy. Manual cache control MUST be exposed through standard tool-pack functions (e.g., `cellpose.cache.clear`) via the existing `run` tool, NOT via a new MCP tool.
- **FR-009**: The system MUST return constitution-aligned structured errors (including `code`, `message`, and `details[]` with `path` and `hint`) for invalid, expired, or incompatible `ObjectRef` instances.
- **FR-010**: Workflow records MUST store the initialization parameters of an `ObjectRef` to enable headless reproducibility.

### Key Entities
- **ObjectRef**: A specialized `ArtifactRef` representing a serialized Python object.
    - **Required Fields**: `uri` (pointer to pickle/state), `python_class` (fully qualified name).
    - **Optional Fields**: `device` (execution device, e.g., 'cpu', 'cuda'), `sha256` (hash of state for integrity), `init_params` (dict of parameters used for reconstruction).

## Non-Functional Requirements

### Architectural Constraints
- **Stable MCP Surface**: Exactly 8 tools must be maintained (no new MCP tools). State management is internal or via existing `run` calls.
- **Artifact References Only**: Large Python objects MUST NOT be embedded in MCP messages; only `ObjectRef` pointers are exchanged.
- **Reproducibility**: All `ObjectRef` instances must be exportable and replayable via the `NativeOutputRef` (workflow record) mechanism.
- **Observability**: All object lifecycle events (instantiation, eviction, reconstruction) MUST be logged to structured logs.

### Performance
- **SC-003 Performance**: Success criteria SC-003 (>= 2x speedup for iterative calls) is the primary performance benchmark.

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: The `list` and `describe` tools correctly display `cellpose.models.CellposeModel.eval` as an available function.
- **SC-002**: The `describe` output for `CellposeModel.eval` correctly identifies `ObjectRef` as the required type for the `self` (instance) parameter.
- **SC-003**: Executing `eval` with a pre-instantiated `ObjectRef` is at least 2x faster than a "cold-start" execution that includes model loading.
- **SC-004**: The `train_seg` function successfully returns a `NativeOutputRef` for the resulting model weights and a `TableRef` containing training loss statistics.
