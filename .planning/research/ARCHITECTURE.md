# Architecture Research: Interactive Annotation

## Current Architecture Summary
The `bioimage-mcp` server uses a **hub-and-spoke** architecture:
- **Core Server (MCP):** Python 3.13 server with `stdio` transport, handling protocol, sessions, and tool discovery.
- **Persistent Workers:** Long-lived subprocesses managed by `PersistentWorkerManager`, which reuse conda environments to eliminate startup overhead.
- **NDJSON IPC:** Communication between the core and workers via `stdin/stdout` pipes using Line-Delimited JSON.
- **Artifact System:** Data is passed via persistent references (`BioImageRef`, `ObjectRef`, etc.) backed by File, S3, or Memory storage.

## Integration Challenge
Interactive annotation (napari + µSAM) differs fundamentally from "fire-and-forget" batch tools:
1. **Blocking Lifecycle:** GUI applications like napari require a blocking event loop (`gui_qt()`) that prevents the worker from responding to standard NDJSON requests on the same thread.
2. **Plugin Reuse:** We are **reusing the micro-sam napari plugin** which already provides all annotation UI (prompts, preview, undo/redo, 3D propagation). Our work is launching the plugin and bridging artifacts.
3. **Hardware Locality:** The GUI must open on the host machine. This architecture assumes **Local MCP** usage (e.g., Claude Desktop on the same machine as the bioimage-mcp server).
4. **State Persistence:** Segmenting a large image involves "Session State" (embeddings, current masks) that must survive across user refinements.

## Proposed Architecture Options

### Option 1: Synchronous Blocking Worker (Recommended for v0.5.0)
The MCP tool call launches napari and blocks the worker process until the window is closed.
- **Tradeoffs:** Simplest to implement; directly utilizes the existing `PersistentWorker` infrastructure.
- **Mechanism:** The tool handler in the worker starts the napari event loop. On closure, it writes the result to a new artifact and returns the final NDJSON response.

### Option 2: Sidecar Interactive Server
The tool starts a separate "Annotation Sidecar" process (HTTP/WebSocket) that hosts napari.
- **Tradeoffs:** Decouples GUI from the worker pipe; allows background status updates.
- **Mechanism:** The worker returns a status URL; the agent or user monitors the session independently. Overkill for local execution but better for remote.

## Recommended Approach: Stateful Interaction Bridge
We recommend **Option 1** with **Embedding Caching** and **Subprocess Isolation**.

1. **Persistent Worker for µSAM:** A dedicated tool pack environment containing `napari`, `micro-sam`, and `pytorch`.
2. **Embedding Cache (ObjectRef):** SAM embeddings are stored in the worker's `_OBJECT_CACHE` as `ObjectRef` artifacts. This allows a user to "Re-open Annotation" instantly without re-calculating heavy vision transformer (ViT) embeddings.
3. **Subprocess Isolation:** The tool runner spawns a separate `napari_host.py` process to isolate the Qt event loop from the worker's IPC pipe.

## New Components Needed

### 1. `micro-sam` Tool Pack
Located in `tools/micro_sam/`:
- `compute_embeddings(image)`: Pre-calculates SAM embeddings and returns an `ObjectRef`.
- `annotate(image, embeddings)`: Launches napari with the **micro-sam plugin** (reusing its UI), loading the image from artifacts.
- `segment_automatic(image)`: Headless zero-shot segmentation.

### 2. `ArtifactBridge` (Internal Utility)
A helper class to manage the transition from:
- `BioImageRef` (input) → napari Image layer (via napari-ome-zarr)
- napari Labels layer → `BioImageRef` (output, OME-Zarr export)

**Note:** The micro-sam plugin provides its own UI including the commit button. We hook into layer state on window close.

### 3. `SessionManager` (Internal Utility)
Logic within the worker to:
- Track embedding cache (keyed by image hash)
- Handle window close events and artifact persistence
- Manage orphan cleanup if parent process terminates

## Data Flow
1. **Initiate:** AI Agent calls `micro_sam.annotate(image_artifact)`.
2. **Spawning:** MCP Server dispatches to a persistent `bioimage-mcp-microsam` worker.
3. **Interactive Subprocess:** Worker spawns napari with **micro-sam plugin loaded** in a child process.
4. **Artifact Load:** `ArtifactBridge` loads OME-Zarr image into napari Image layer.
5. **Inference Loop (Plugin-Managed):** 
   - User interacts with micro-sam plugin UI (points, boxes, scribbles)
   - Plugin handles inference loop internally ($<100ms$ per prompt)
   - All annotation features provided by plugin, not custom code
6. **Completion:** User closes napari window (or uses plugin's commit).
7. **Serialization:** `ArtifactBridge` exports Labels layer to OME-Zarr artifact.
8. **Response:** Worker returns the `BioImageRef` artifact to the MCP server.

## Build Order

1. **Environment Definition:** Create `bioimage-mcp-microsam` conda environment with GPU support.
2. **Headless SAM Tools:** Implement `compute_embeddings` and `segment_automatic` to verify model weights and basic inference.
3. **Napari Bridge:** Implement the blocking GUI launcher in the tool handler with subprocess isolation.
4. **Commit/Sync Logic:** Implement the "Commit" button and OME-Zarr export from napari layers.
5. **Interactive Chaining:** Enable the agent to suggest `annotate` after a failed automatic segmentation.

## Patterns to Follow

### Pattern 1: Subprocess Isolation
Always run the GUI in a separate process to prevent blocking the worker's IPC loop and to ensure `PyQt` doesn't conflict with other server-side dependencies.

### Pattern 2: Model State Caching
Store SAM embeddings in a cache tied to the image hash. This allows the user to close and reopen the viewer without waiting for the 30-second precomputation step again.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Threaded GUI
Running napari in a thread (`threading.Thread`) within the server process. Qt often causes segmentation faults or deadlocks when mixed with complex server logic on different threads.

### Anti-Pattern 2: Large Data over Pipes
Passing huge NumPy arrays via stdin/stdout pipes between the worker and napari. This is slow and prone to buffer overflows. Use shared local files or artifacts.

## Sources
- [micro-sam Documentation](https://computational-cell-analytics.github.io/micro-sam/micro_sam.html)
- [napari Plugin Architecture](https://napari.org/stable/plugins/index.html)
- [MCP Specification: Resources and Tools](https://modelcontextprotocol.io/)
