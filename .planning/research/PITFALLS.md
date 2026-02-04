# Pitfalls Research: Interactive Annotation

**Domain:** napari + µSAM Interactive Annotation
**Researched:** 2026-02-04
**Confidence:** HIGH

This research identifies critical risks when adding GUI-based interactive tools (napari) and foundation models (SAM) to the `bioimage-mcp` server.

## Critical Pitfalls

### 1. Blocking the MCP Server Event Loop
**What goes wrong:** Calling `napari.run()` or creating a `napari.Viewer` directly in the MCP server's main thread blocks the `asyncio` loop.
**Why it happens:** napari/Qt requires a blocking event loop on the main thread. MCP servers expect to be always-available listeners.
**Consequences:** The server becomes unresponsive to status polls, subsequent tool calls, or shutdown signals. The orchestrator (e.g., Claude) will report a timeout.
**Prevention:** 
- Spawn the interactive viewer in a **separate subprocess** using `multiprocessing` or `subprocess.Popen`.
- Use a dedicated `InteractiveSessionManager` to track the lifecycle of the GUI process.
**Warning signs:** Log output stops exactly when the viewer is requested; CPU usage drops but window doesn't appear for seconds.
**Phase to address:** Phase 1 (Core Integration).

### 2. Orphaned GUI Processes & Memory Leaks
**What goes wrong:** If the MCP server is terminated (e.g., user kills the client), the napari window and its Python process remain active, holding onto valuable GPU VRAM.
**Why it happens:** Subprocesses don't always die with their parent unless explicitly managed.
**Consequences:** "CUDA out of memory" errors on subsequent runs; zombie python processes consuming system resources.
**Prevention:** 
- Implement a "watchdog" inside the napari process that checks if the parent MCP server is still alive.
- Use `atexit` handlers and explicit cleanup on server shutdown.
**Warning signs:** `nvidia-smi` shows memory usage when no analysis is running; "Address already in use" errors on restart.
**Phase to address:** Phase 1 (Lifecycle Management).

### 3. Data Sync & Artifact Loss
**What goes wrong:** The user performs detailed manual annotations in napari, but the results are never saved back to the `bioimage-mcp` artifact store.
**Why it happens:** Standard napari workflows expect users to click "File > Save", which isn't connected to the MCP's automated artifact management.
**Consequences:** Interactive work is lost; agents receive "Success" but the output files are empty.
**Prevention:** 
- Inject a "Commit and Close" button into the napari interface using `magicgui`.
- Block the default window "X" or prompt to save before closing.
**Warning signs:** Tool returns without creating an output artifact; discrepancy between what user sees and what agent processes.
**Phase to address:** Phase 2 (Annotation UX).

## napari-Specific Issues

### 1. Big-Data UI Lag (The "Labels" Bottleneck)
**What goes wrong:** Large 3D microscopy volumes or dense `Labels` layers cause the napari canvas to stutter during painting or scrolling.
**Prevention:** Use `dask` or tiled arrays for image data. Limit active interactive calculations to the currently visible 2D slice or a small ROI.
**Phase to address:** Phase 3 (Performance).

### 2. Multi-Layer Ambiguity
**What goes wrong:** A user might create multiple `Labels` or `Shapes` layers. The server might pick the wrong one to save as the final result.
**Prevention:** Establish a naming convention (e.g., `labels_result`) and programmatically lock or mark the primary output layer.
**Phase to address:** Phase 2 (Annotation UX).

## µSAM-Specific Issues

### 1. Precomputation "Blackout"
**What goes wrong:** SAM requires precomputing embeddings for the entire image before interaction starts. This can take 5-30s on a GPU, during which the UI appears frozen.
**Prevention:** Use `napari.qt.threading.thread_worker` to compute embeddings in the background while showing a progress bar in the napari status bar.
**Warning signs:** UI unresponsive for several seconds after selecting an image.

### 2. First-Run Model Download Latency
**What goes wrong:** Specialist models (e.g., `vit_l_lm`) are large (>1GB). The first time they are used, they are downloaded from Zenodo/BioImage.IO.
**Prevention:** Explicitly trigger model downloads during tool-pack installation or show a dedicated "Downloading Model..." status message to prevent the user from killing the process.
**Phase to address:** Phase 2 (SAM Integration).

### 2. VRAM Over-Allocation
**What goes wrong:** Loading a SAM "huge" model (`sam_h`) plus image embeddings and napari UI can exceed 8GB VRAM.
**Prevention:** Default to `vit_b` (base) or `vit_l` (large). Provide a way to specify the model type based on host hardware capabilities.
**Phase to address:** Phase 3 (Optimization).

## Integration Pitfalls

### 1. Path Mapping (Local vs Container)
**What goes wrong:** If the MCP server is in a container (e.g. Docker), the path to an artifact inside the container (`/app/data/...`) is invisible to a napari process running on the host.
**Prevention:** Use a shared mount or ensure the server and GUI are running in the same filesystem context.
**Phase to address:** Phase 1 (Infrastructure).

### 2. Headless Environment Failure
**What goes wrong:** The MCP server is running on a headless remote server (SSH/Cloud). Launching napari fails immediately because there is no display.
**Prevention:** Detect the absence of a display (e.g. `DISPLAY` env var) and return a clear error explaining that interactive tools require a GUI-capable environment.
**Phase to address:** Phase 4 (Deployment).

## Platform Pitfalls

### 1. WSL2/WSLg Performance
**What goes wrong:** OpenGL acceleration in WSL2 is often unconfigured or slow, making napari 3D rendering unusable.
**Prevention:** Document the requirement for WSLg and specific NVIDIA driver versions. Verify acceleration on startup.

### 2. macOS Apple Silicon (MPS vs CUDA)
**What goes wrong:** Standard µSAM examples use `device="cuda"`. On macOS, this will crash.
**Prevention:** Use `micro_sam.util.get_device()` to automatically detect `cuda`, `mps`, or `cpu`.

## Prevention Checklist

- [ ] **Subprocess:** Is napari running in its own process, isolated from the MCP server's main loop?
- [ ] **Watchdog:** Does the napari process terminate if the parent MCP server dies?
- [ ] **Save Button:** Is there a prominent "Commit" button to signal completion to the MCP server?
- [ ] **Feedback:** Does the user see a progress bar during model loading and embedding?
- [ ] **Device Detection:** Does the code handle CUDA, MPS (macOS), and CPU fallbacks?
- [ ] **Artifact Mapping:** Are file paths correctly mapped between the server and the GUI process?

---
*Pitfalls research for: napari + µSAM Interactive Annotation*
*Researched: 2026-02-04*
