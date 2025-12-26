# Research: Phasor Usability Fixes

## Research Findings

### Issue 1: Discovery Infrastructure Failure (ServerSession Error)

**Decision**: Use `id(ctx.session)` as a memory-based session identifier fallback.

**Rationale**: 
- The MCP Python SDK v1.25.0 does not provide a `.id` attribute on ServerSession
- The TypeScript SDK has this attribute but Python SDK does not
- Using `id(ctx.session)` provides a stable connection-scoped identifier
- For SSE transport, query params can provide session_id

**Alternatives Considered**:
1. `ctx.request_id` - Changes per request, not suitable for session-scoped state
2. Client-provided `_meta.client_id` - Not guaranteed to be present
3. Generate UUID on first call - Loses session association on reconnect

**Implementation Approach**:
- Create `get_session_identifier(ctx)` helper function
- First try SSE query params, then fallback to `id(ctx.session)`
- Replace all `ctx.session.id` references with this helper

### Issue 2: Empty Schema from describe_function

**Decision**: Fix the `meta.describe` entrypoint to return complete params_schema from Pydantic models.

**Rationale**:
- The schema enrichment system (`describe_function` -> `meta.describe` -> cache) is designed correctly
- The issue is that `meta.describe` is not finding/returning the schema properly
- Need to verify the `meta.describe` implementation in the base toolkit returns proper JSON Schema

**Alternatives Considered**:
1. Hardcode schemas in manifest.yaml - Violates summary-first principle
2. Skip dynamic introspection - Loses type accuracy from Pydantic models

**Implementation Approach**:
- Investigate `meta.describe` implementation in `tools/base/bioimage_mcp_base/entrypoint.py`
- Ensure it can introspect both static (manifest-defined) and dynamic (adapter-discovered) functions
- Add tests for schema enrichment

### Issue 3: Phasor Calibration

**Decision**: Wrap `phasorpy.lifetime.phasor_calibrate` as a new `base.phasor_calibrate` function.

**Rationale**:
- phasorpy provides complete calibration implementation
- The mathematical model (phase shift + modulation ratio) is well-tested
- Wrapping avoids reimplementing complex FLIM math

**Calibration Algorithm**:
1. Compute reference phasor center (mean G, mean S)
2. Compute theoretical phasor from known lifetime: g_theory = 1/(1+(ωτ)²), s_theory = ωτ/(1+(ωτ)²)
3. Compute phase shift: Δφ = arctan(s_theory/g_theory) - arctan(s_ref/g_ref)
4. Compute modulation ratio: M_ratio = sqrt(g_theory² + s_theory²) / sqrt(g_ref² + s_ref²)
5. Transform sample phasors: rotate by Δφ and scale by M_ratio

**Alternatives Considered**:
1. Add calibration to phasor_from_flim - Violates single-responsibility
2. Implement from scratch - Duplicates well-tested phasorpy code

**Implementation Approach**:
- Add `base.phasor_calibrate` to manifest.yaml
- Implement wrapper in transforms.py
- Accept 2-channel BioImageRef for sample phasors, 2-channel for reference phasors
- Output 2-channel BioImageRef (G in channel 0, S in channel 1)
- Parameters: `lifetime` (float), `frequency` (float), `harmonic` (int, default 1)

### Issue 4: bioio-bioformats Integration

**Decision**: Add bioio-bioformats and OpenJDK to the base environment, implement explicit fallback chain.

**Rationale**:
- bioio does not auto-fallback on execution errors
- bioio-bioformats handles more OME-TIFF variants (including AnnotationRef)
- Explicit try-except chain gives predictable behavior

**Java Requirements**:
- OpenJDK 11+ (from conda-forge)
- scyjava for Python-JVM bridge
- JAVA_HOME set to $CONDA_PREFIX

**Fallback Priority**:
1. bioio-ome-tiff (fast, pure Python)
2. bioio-bioformats (heavier, Java-based, more compatible)
3. tifffile (minimal, raw pixels only)

**Alternatives Considered**:
1. Only use bioio-bioformats - Too heavy for simple files
2. Only use tifffile - Loses metadata

**Implementation Approach**:
- Update envs/bioimage-mcp-base.yaml with openjdk, scyjava, bioio-bioformats
- Implement `load_image_fallback()` in tools/base/bioimage_mcp_base/io.py
- Emit warnings on fallback to lower-priority reader

## Dependencies Summary

| Dependency | Version | Purpose |
|------------|---------|---------|
| mcp | >=1.25.0 | MCP Python SDK (ServerSession handling) |
| phasorpy | any | Phasor transform and calibration |
| bioio-bioformats | any | OME-TIFF reader with broad compatibility |
| openjdk | >=11 | Java runtime for bioio-bioformats |
| scyjava | any | Python-Java bridge |

## Open Questions (All Resolved)

- ✅ Q: How to identify sessions without ServerSession.id? → A: Use `id(ctx.session)`
- ✅ Q: Where is schema enrichment failing? → A: Needs meta.describe investigation
- ✅ Q: What phasorpy API to use for calibration? → A: `phasorpy.lifetime.phasor_calibrate`
- ✅ Q: What Java version for bioformats? → A: OpenJDK 11+
