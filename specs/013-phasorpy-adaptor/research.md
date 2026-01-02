# Research: Phasorpy Adaptor (v0.13)

## 1. Dynamic Discovery Approach
- **Decision**: Use `inspect` and `importlib` for full dynamic discovery of phasorpy modules.
- **Rationale**: Phasorpy is evolving rapidly (v0.9+). Manual updates are error-prone and will lag behind the library. The current adapter only exposes 2 of 75+ functions. Dynamic discovery ensures the MCP server automatically supports new functionality as the library grows.
- **Alternatives Considered**: 
  - **Manual hardcoded manifest entries**: Rejected as unmaintainable for 75+ functions and high risk of becoming outdated.
  - **Static code generation**: Rejected because it requires regeneration on every phasorpy update, adding friction to the development cycle.

## 2. I/O Pattern Extension
- **Decision**: Add new `IOPattern` enum values for phasor-specific operations.
- **Rationale**: Phasor analysis has unique I/O shapes not covered by existing image-to-image patterns. Specifically, operations that calculate lifetimes (SCALAR) or generate visualizations (PLOT) require distinct classifications for agent routing.
- **New patterns to add**: 
  - `PHASOR_TO_SCALAR`: For lifetime calculations.
  - `PLOT`: For matplotlib figure capture.
  - `SCALAR_TO_PHASOR`: For `phasor_from_lifetime`.
- **Alternatives Considered**: 
  - **Reusing existing patterns**: Rejected because it would lead to ambiguous tool selection for agents (e.g., PHASOR_TRANSFORM vs. PHASOR_TO_SCALAR).

## 3. PlotRef Artifact Type
- **Decision**: Add a new `PlotRef` artifact type for matplotlib figure capture.
- **Rationale**: Phasorpy plotting functions return matplotlib figures that must be captured as artifacts to be useful in an MCP context. The current system only supports image, table, and log references.
- **Format**: PNG (most compatible with MCP clients).
- **Metadata**: `width_px`, `height_px`, `dpi`, `plot_type`.
- **Implementation**: Detect `matplotlib.figure.Figure` returns in the adapter's `execute` method, call `fig.savefig()` to a temporary PNG, and register as a `PlotRef`.
- **Alternatives Considered**: 
  - **Converting plots to BioImageRef**: Rejected because plots are 2D visualizations (PNG/JPG), not scientific multi-dimensional images.
  - **Sending raw plot data**: Rejected because it violates Constitution Principle III (never embed large binaries in MCP messages).

## 4. Module Inclusion/Exclusion
- **Decision**: Exclude the `phasorpy.io` module from the adapter.
- **Rationale**: All file I/O must be handled via `bioio` plugins (e.g., `bioio-bioformats` for SDT/PTU, `bioio-lif` for LIF) to maintain consistency with Constitution Principle III (artifact references via bioio). Allowing `phasorpy.io` would create a parallel, non-standard I/O path.
- **Modules to include**: `phasorpy.phasor`, `phasorpy.lifetime`, `phasorpy.plot`, `phasorpy.filter`, `phasorpy.cursor`, `phasorpy.component`.
- **Alternatives Considered**: 
  - **Including all modules**: Rejected to prevent I/O fragmentation and maintain the single source of truth for image loading.

## 5. Multi-Output Handling
- **Decision**: Functions returning tuples produce multiple artifact outputs.
- **Rationale**: Many Phasorpy functions (e.g., `phasor_from_signal`) return multiple related arrays (mean, real, imag). Mapping these to multiple output artifacts allows agents to track provenance for each component individually.
- **Naming convention**: Parse docstrings for return names; fallback to `output_0`, `output_1`, etc., if names cannot be extracted.
- **Example**: `phasor_from_signal` returns `(mean, real, imag)` → 3 BioImageRef artifacts.
- **Alternatives Considered**: 
  - **Packaging outputs into a single Zarr group**: Rejected as it makes individual component access harder for simple tools and obscures the API surface.

## 6. Subprocess Isolation
- **Decision**: Phasorpy executes in the `bioimage-mcp-base` environment via a persistent worker.
- **Rationale**: Constitution Principle II requires isolated tool execution. Heavy dependencies like `matplotlib` and `numpy` C-extensions must stay out of the core server environment to prevent crashes and dependency conflicts.
- **Error handling**: Worker crash detection captures C-extension errors (segmentation faults, etc.) and reports them as a `TERMINATED` state with logs.
- **Alternatives Considered**: 
  - **Running in core server**: Rejected due to Constitution violation and risk of server instability.

## 7. Dimension Hints for Agents
- **Decision**: Add dimension hints to function metadata.
- **Rationale**: Phasorpy functions have `axis` parameters that are critical for correct operation (e.g., "use axis=-1 for decay dimension"). Without hints, LLMs often guess axes incorrectly for high-dimensional data.
- **Implementation**: `generate_dimension_hints()` method on the adapter will inspect function signatures and provided metadata to suggest default axes based on the artifact's metadata.
- **Alternatives Considered**: 
  - **Hardcoding axes in manifests**: Rejected because axes depend on the specific input data shape and the tool's intended use.
