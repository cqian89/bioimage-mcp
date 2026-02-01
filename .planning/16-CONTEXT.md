# Phase 16 Context: StarDist Tool Environment

## Domain Analysis
StarDist is a deep-learning-based nucleus detection library. Unlike typical functional libraries, it uses a class-based API (`StarDist2D`, `StarDist3D`) where a model is instantiated (loading weights) and then methods like `predict_instances` are called. It requires TensorFlow.

## Key Decisions

### 1. Model Management
- **Strategy:** Use StarDist's native caching mechanism (typically `~/.keras/`). Do not enforce a custom `~/.bioimage-mcp` cache location for internal model files.
- **Downloading:** Lazy download. Models are downloaded automatically by StarDist the first time they are requested in the constructor.
- **Bundling:** Do **not** bundle models in the docker/conda environment. All models are fetched on demand.
- **Custom Models:** The API must support passing local file paths to the constructor for custom-trained models.

### 2. API Surface & Introspection
- **Exposure Pattern:** **Class Exposure**. Do not create a simplified functional wrapper (e.g., `stardist_predict`). Instead, expose the `StarDist2D` and `StarDist3D` classes directly using the Unified Introspection Engine.
- **Scope:** Include both **Inference** (`predict_instances`, `predict_big`) and **Training** (`train`) capabilities.
- **Parameters:** Expose all native parameters via introspection. Do not hide advanced parameters behind a `params` dict unless that's the native API.

### 3. I/O & Artifacts
- **Return Values:** Keep the native return signature `(labels, details)`. The introspection engine should handle this as a Tuple artifact or similar.
- **Details Dict:** Return the `details` dictionary (containing `coord`, `prob`, `dist`) as a generic Dictionary artifact. Arrays within it will be serialized as standard lists or nested arrays.
- **Label Images:** The `labels` output must be returned as an OME-Zarr artifact (handled via the standard IO bridge).
- **Training Data:** The training methods should accept both:
    - Paths to directories containing images/masks.
    - Lists of Image artifacts.

### 4. Environment & Hardware
- **TensorFlow:** **GPU Enabled**. The environment should support GPU acceleration by default (e.g., `tensorflow` with CUDA support).
- **Source:** Install `stardist` and `tensorflow` via **conda-forge**.
- **Logging:** Suppress TensorFlow noise (e.g., set `TF_CPP_MIN_LOG_LEVEL=2`).
- **Memory:** Use default TensorFlow memory allocation strategy.

## Implementation Guidance
- **Manifest:** Create `tools/stardist/manifest.yaml` pointing to the `stardist` module/classes.
- **Env:** Create `envs/stardist.yml` with `stardist`, `tensorflow`, and `bioimage-mcp-core`.
- **Introspection:** Ensure the unified introspection engine correctly handles:
    - Class constructors (`__init__`) for model loading.
    - Method signatures for `predict_instances`.
    - Tuple return types.
