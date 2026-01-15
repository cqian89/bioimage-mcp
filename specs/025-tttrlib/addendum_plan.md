# Implementation Plan: tttrlib Expansion (v0.2.0 - v0.3.0)

## Overview

This plan covers the implementation of 4 new CLSMImage methods to enable cross-tool workflows with PhasorPy and Cellpose:

- **v0.2.0**: `get_intensity()`, `get_phasor()`, `get_fluorescence_decay()` - enables PhasorPy bridge
- **v0.3.0**: `get_mean_lifetime()` - enables Cellpose bridge

## Prerequisite: v0.1.0 Schema Drift Fix

Before adding new CLSMImage methods, align the curated schema (`tools/tttrlib/schema/tttrlib_api.json`) with the actual tool surface (manifest + `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py`):
- `tttrlib.TTTR.container_type` enum values (notably `PHOTON-HDF5`)
- `tttrlib.CLSMImage` params (include `n_frames`)
- `tttrlib.TTTR.write` output key (`tttr_out`)

## Milestone 1: v0.2.0 - PhasorPy Integration

### Goal
Enable two pathways from TTTR data to PhasorPy analysis:
- **Pathway A**: TTTR → CLSMImage → get_phasor(tttr_data=TTTR) → phasorpy.plot/phasor_transform
- **Pathway B**: TTTR → CLSMImage → get_fluorescence_decay(tttr_data=TTTR) → phasorpy.phasor_from_signal

### Phase 1: get_intensity() Implementation

#### 1.1 Schema Updates

Add to `tools/tttrlib/schema/tttrlib_api.json`:
```json
"tttrlib.CLSMImage.get_intensity": {
  "summary": "Extract intensity image from CLSM data",
  "inputs": {
    "clsm": {
      "artifact_type": "ObjectRef",
      "required": true
    }
  },
  "params": {
    "stack_frames": {
      "type": "boolean",
      "default": false,
      "description": "Sum intensity across all frames into a single 2D image"
    }
  },
  "outputs": {
    "intensity": {
      "artifact_type": "BioImageRef",
      "format": "OME-TIFF",
      "description": "3D array (Z,Y,X) or 2D (Y,X) if stack_frames=true"
    }
  }
}
```

#### 1.2 Manifest Updates

Add to `tools/tttrlib/manifest.yaml`:
```yaml
- fn_id: tttrlib.CLSMImage.get_intensity
  tool_id: tools.tttrlib
  name: Get Intensity Image
  description: Extract intensity image (photon counts per pixel) from CLSM data
  tags: [imaging, intensity, clsm]
  inputs:
    - name: clsm
      artifact_type: ObjectRef
      required: true
  outputs:
    - name: intensity
      artifact_type: BioImageRef
      format: OME-TIFF
      required: true
  params_schema:
    type: object
    properties:
      stack_frames:
        type: boolean
        default: false
        description: "Sum across all frames into single 2D image"
```

#### 1.3 Handler Implementation

Add to `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py`:

```python
def handle_get_intensity(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.CLSMImage.get_intensity - extract intensity image."""
    import numpy as np
    from bioio.writers import OmeTiffWriter

    clsm_ref = inputs.get("clsm", {})
    clsm_key = clsm_ref.get("uri") or clsm_ref.get("ref_id") or ""

    try:
        clsm = _load_object(clsm_key)
        
        # Get intensity array from CLSMImage
        # tttrlib API: CLSMImage.get_intensity() -> (n_frames, n_lines, n_pixel)
        intensity = np.asarray(clsm.get_intensity())
        
        stack_frames = params.get("stack_frames", False)
        if stack_frames:
            # Sum across frames to get 2D image
            intensity = intensity.sum(axis=0)
            dim_order = "YX"
        else:
            dim_order = "ZYX"  # Frames as Z
        
        out_path = work_dir / f"intensity_{uuid.uuid4().hex[:8]}.ome.tif"
        OmeTiffWriter.save(intensity, str(out_path), dim_order=dim_order)
        
        output = {
            "ref_id": uuid.uuid4().hex,
            "type": "BioImageRef",
            "uri": f"file://{out_path.absolute()}",
            "path": str(out_path.absolute()),
            "format": "OME-TIFF",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "axes": dim_order,
                "shape": list(intensity.shape),
                "dtype": str(intensity.dtype),
            }
        }
        
        return {"ok": True, "outputs": {"intensity": output}, "log": "Intensity extracted"}
    
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}
```

#### 1.4 Tests (TDD)

**Contract test** (`tests/contract/test_tttrlib_manifest.py`):
```python
def test_get_intensity_in_manifest():
    """Verify get_intensity function is defined in manifest."""
    manifest = load_manifest("tools/tttrlib/manifest.yaml")
    fn_ids = [f["fn_id"] for f in manifest["functions"]]
    assert "tttrlib.CLSMImage.get_intensity" in fn_ids
```

**Smoke test** (`tests/smoke/test_tttrlib_intensity.py`):
```python
@pytest.mark.smoke_full
@pytest.mark.requires_env("bioimage-mcp-tttrlib")
async def test_intensity_extraction(live_server):
    """Test TTTR → CLSMImage → intensity → BioImageRef"""
    # 1. Open TTTR
    # 2. Create CLSMImage
    # 3. Get intensity
    # 4. Verify BioImageRef with correct shape
```

### Phase 2: get_phasor() Implementation

#### 2.1 Schema Updates

Add to `tools/tttrlib/schema/tttrlib_api.json`:
```json
"tttrlib.CLSMImage.get_phasor": {
  "summary": "Compute phasor coordinates (g, s) per pixel",
  "inputs": {
    "clsm": {
      "artifact_type": "ObjectRef",
      "required": true
    },
    "tttr_data": {
      "artifact_type": "TTTRRef",
      "required": true,
      "description": "Original TTTR data for microtime access"
    },
    "tttr_irf": {
      "artifact_type": "TTTRRef",
      "required": false,
      "description": "IRF data for correction"
    }
  },
  "params": {
    "frequency": {
      "type": "number",
      "default": -1.0,
      "description": "Modulation frequency in MHz. -1 to auto-detect from header"
    },
    "harmonic": {
      "type": "integer",
      "default": 1,
      "description": "Harmonic for multi-harmonic phasor analysis"
    },
    "minimum_number_of_photons": {
      "type": "integer",
      "default": 2,
      "description": "Minimum photons per pixel for valid phasor"
    },
    "stack_frames": {
      "type": "boolean",
      "default": false,
      "description": "Combine frames before phasor calculation"
    }
  },
  "outputs": {
    "phasor": {
      "artifact_type": "BioImageRef",
      "format": "OME-TIFF",
      "description": "4D array (F,Y,X,2) where last dim is [g, s]"
    }
  }
}
```

#### 2.2 Handler Implementation

```python
def handle_get_phasor(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.CLSMImage.get_phasor - compute phasor image."""
    import numpy as np
    from bioio.writers import OmeTiffWriter

    clsm_ref = inputs.get("clsm", {})
    clsm_key = clsm_ref.get("uri") or clsm_ref.get("ref_id") or ""
    
    tttr_ref = inputs.get("tttr_data", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""
    
    tttr_irf_ref = inputs.get("tttr_irf")

    try:
        clsm = _load_object(clsm_key)
        tttr_data = _load_tttr(tttr_key)
        
        # Prepare IRF if provided
        tttr_irf = None
        if tttr_irf_ref:
            irf_key = tttr_irf_ref.get("uri") or tttr_irf_ref.get("ref_id") or ""
            if irf_key:
                tttr_irf = _load_tttr(irf_key)
        
        phasor_kwargs = {
            "tttr_data": tttr_data,
            "frequency": params.get("frequency", -1.0),
            "minimum_number_of_photons": params.get("minimum_number_of_photons", 2),
            "stack_frames": params.get("stack_frames", False),
        }
        if tttr_irf is not None:
            phasor_kwargs["tttr_irf"] = tttr_irf
        
        # get_phasor returns array of shape (Z, Y, X, 2) where last dim is [g, s]
        phasor_data = clsm.get_phasor(**phasor_kwargs)
        phasor_data = np.asarray(phasor_data)
        
        # Determine dimension order
        if phasor_data.ndim == 3:  # (Y, X, 2) - stacked
            dim_order = "YXC"
        elif phasor_data.ndim == 4:  # (Z, Y, X, 2)
            dim_order = "ZYXC"  # Z for frames
        else:
            dim_order = "TZYXC"[-phasor_data.ndim:]
        
        out_path = work_dir / f"phasor_{uuid.uuid4().hex[:8]}.ome.tif"
        OmeTiffWriter.save(phasor_data.astype(np.float32), str(out_path), dim_order=dim_order)
        
        output = {
            "ref_id": uuid.uuid4().hex,
            "type": "BioImageRef",
            "uri": f"file://{out_path.absolute()}",
            "path": str(out_path.absolute()),
            "format": "OME-TIFF",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "axes": dim_order,
                "shape": list(phasor_data.shape),
                "dtype": str(phasor_data.dtype),
                "channel_names": ["g", "s"],
                "frequency_mhz": params.get("frequency", -1.0),
            }
        }
        
        return {"ok": True, "outputs": {"phasor": output}, "log": "Phasor computed"}
    
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}
```

#### 2.3 Smoke Test: tttrlib → PhasorPy Pathway A

```python
@pytest.mark.smoke_full
@pytest.mark.requires_env("bioimage-mcp-tttrlib")
async def test_tttr_to_phasorpy_pathway_a(live_server):
    """Test Pathway A: TTTR → CLSMImage → get_phasor → phasorpy.plot"""
    # 1. Open TTTR
    tttr_result = await live_server.call_tool("run", {
        "fn_id": "tttrlib.TTTR",
        "inputs": {},
        "params": {"filename": str(PTU_FILE), "container_type": "PTU"}
    })
    tttr_ref = tttr_result["outputs"]["tttr"]
    
    # 2. Create CLSMImage
    clsm_result = await live_server.call_tool("run", {
        "fn_id": "tttrlib.CLSMImage",
        "inputs": {"tttr": tttr_ref},
        "params": {"reading_routine": "SP5", "channels": [0]}
    })
    clsm_ref = clsm_result["outputs"]["clsm"]
    
    # 3. Get phasor image
    phasor_result = await live_server.call_tool("run", {
        "fn_id": "tttrlib.CLSMImage.get_phasor",
        "inputs": {"clsm": clsm_ref, "tttr_data": tttr_ref},
        "params": {"frequency": 80.0}
    })
    phasor_ref = phasor_result["outputs"]["phasor"]
    assert phasor_ref["type"] == "BioImageRef"
    
    # 4. Plot with phasorpy
    plot_result = await live_server.call_tool("run", {
        "fn_id": "phasorpy.plot.plot_phasor",
        "inputs": {"real": phasor_ref, "imag": phasor_ref}  # Split in implementation
    })
    assert plot_result["status"] == "success"
```

### Phase 3: get_fluorescence_decay() Implementation

#### 3.1 Schema and Handler

Similar to get_phasor, but outputs decay histograms:

```python
def handle_get_fluorescence_decay(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.CLSMImage.get_fluorescence_decay - extract decay histogram per pixel."""
    import numpy as np
    from bioio.writers import OmeTiffWriter

    clsm_ref = inputs.get("clsm", {})
    clsm_key = clsm_ref.get("uri") or clsm_ref.get("ref_id") or ""
    
    tttr_ref = inputs.get("tttr_data", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""

    try:
        clsm = _load_object(clsm_key)
        tttr_data = _load_tttr(tttr_key)
        
        decay_kwargs = {
            "tttr_data": tttr_data,
            "micro_time_coarsening": params.get("micro_time_coarsening", 1),
            "stack_frames": params.get("stack_frames", False),
        }
        
        # get_fluorescence_decay returns (Z, Y, X, T) where T is microtime bins
        decay_data = clsm.get_fluorescence_decay(**decay_kwargs)
        decay_data = np.asarray(decay_data)
        
        # Output as 4D with T as last dimension
        if decay_data.ndim == 3:  # (Y, X, T) - stacked
            dim_order = "YXT"  # T for time bins
        else:  # (Z, Y, X, T)
            dim_order = "ZYXT"
        
        out_path = work_dir / f"decay_{uuid.uuid4().hex[:8]}.ome.tif"
        OmeTiffWriter.save(decay_data.astype(np.float32), str(out_path), dim_order=dim_order)
        
        output = {
            "ref_id": uuid.uuid4().hex,
            "type": "BioImageRef",
            "uri": f"file://{out_path.absolute()}",
            "path": str(out_path.absolute()),
            "format": "OME-TIFF",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "axes": dim_order,
                "shape": list(decay_data.shape),
                "n_microtime_bins": decay_data.shape[-1],
            }
        }
        
        return {"ok": True, "outputs": {"decay": output}, "log": "Decay extracted"}
    
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}
```

#### 3.2 Smoke Test: tttrlib → PhasorPy Pathway B

```python
@pytest.mark.smoke_full
async def test_tttr_to_phasorpy_pathway_b(live_server):
    """Test Pathway B: TTTR → decay → phasorpy.phasor_from_signal"""
    # 1-2. Open TTTR and create CLSMImage (as above)
    
    # 3. Get fluorescence decay
    decay_result = await live_server.call_tool("run", {
        "fn_id": "tttrlib.CLSMImage.get_fluorescence_decay",
        "inputs": {"clsm": clsm_ref, "tttr_data": tttr_ref},
        "params": {"micro_time_coarsening": 4}
    })
    decay_ref = decay_result["outputs"]["decay"]
    
    # 4. Compute phasor with phasorpy
    phasor_result = await live_server.call_tool("run", {
        "fn_id": "phasorpy.phasor.phasor_from_signal",
        "inputs": {"signal": decay_ref},
        "params": {"frequency": 80.0}
    })
    assert phasor_result["status"] == "success"
```

## Milestone 2: v0.3.0 - Cellpose Integration

### Goal
Enable TTTR → intensity → Cellpose segmentation → per-cell analysis

### Phase 4: get_mean_lifetime() Implementation

#### 4.1 Schema and Handler

```python
def handle_get_mean_lifetime(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.CLSMImage.get_mean_lifetime - compute lifetime image."""
    import numpy as np
    from bioio.writers import OmeTiffWriter

    clsm_ref = inputs.get("clsm", {})
    clsm_key = clsm_ref.get("uri") or clsm_ref.get("ref_id") or ""
    
    tttr_ref = inputs.get("tttr_data", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""
    
    tttr_irf_ref = inputs.get("tttr_irf")

    try:
        clsm = _load_object(clsm_key)
        tttr_data = _load_tttr(tttr_key)
        
        lifetime_kwargs = {
            "tttr_data": tttr_data,
            "minimum_number_of_photons": params.get("minimum_number_of_photons", 3),
            "stack_frames": params.get("stack_frames", False),
        }
        
        # IRF for accurate lifetime calculation
        if tttr_irf_ref:
            irf_key = tttr_irf_ref.get("uri") or tttr_irf_ref.get("ref_id") or ""
            if irf_key:
                lifetime_kwargs["tttr_irf"] = _load_tttr(irf_key)
        
        # get_mean_lifetime returns (Z, Y, X) in nanoseconds
        lifetime_data = clsm.get_mean_lifetime(**lifetime_kwargs)
        lifetime_data = np.asarray(lifetime_data)
        
        dim_order = "YX" if lifetime_data.ndim == 2 else "ZYX"
        
        out_path = work_dir / f"lifetime_{uuid.uuid4().hex[:8]}.ome.tif"
        OmeTiffWriter.save(lifetime_data.astype(np.float32), str(out_path), dim_order=dim_order)
        
        output = {
            "ref_id": uuid.uuid4().hex,
            "type": "BioImageRef",
            "uri": f"file://{out_path.absolute()}",
            "path": str(out_path.absolute()),
            "format": "OME-TIFF",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "axes": dim_order,
                "shape": list(lifetime_data.shape),
                "unit": "nanoseconds",
            }
        }
        
        return {"ok": True, "outputs": {"lifetime": output}, "log": "Lifetime computed"}
    
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}
```

### Phase 5: Smoke Test - tttrlib → Cellpose Workflow

```python
@pytest.mark.smoke_full
@pytest.mark.requires_env("bioimage-mcp-tttrlib")
@pytest.mark.requires_env("bioimage-mcp-cellpose")
async def test_tttr_to_cellpose_workflow(live_server):
    """Test TTTR → intensity → Cellpose → per-cell lifetime analysis"""
    # 1. Open TTTR
    tttr_result = await live_server.call_tool("run", {
        "fn_id": "tttrlib.TTTR",
        "inputs": {},
        "params": {"filename": str(PTU_FILE), "container_type": "PTU"}
    })
    tttr_ref = tttr_result["outputs"]["tttr"]
    
    # 2. Create CLSMImage
    clsm_result = await live_server.call_tool("run", {
        "fn_id": "tttrlib.CLSMImage",
        "inputs": {"tttr": tttr_ref},
        "params": {"reading_routine": "SP5", "channels": [0]}
    })
    clsm_ref = clsm_result["outputs"]["clsm"]
    
    # 3. Get intensity image
    intensity_result = await live_server.call_tool("run", {
        "fn_id": "tttrlib.CLSMImage.get_intensity",
        "inputs": {"clsm": clsm_ref},
        "params": {"stack_frames": True}  # 2D for Cellpose
    })
    intensity_ref = intensity_result["outputs"]["intensity"]
    
    # 4. Initialize Cellpose model
    model_result = await live_server.call_tool("run", {
        "fn_id": "cellpose.models.CellposeModel",
        "inputs": {},
        "params": {"model_type": "cyto3"}
    })
    model_ref = model_result["outputs"]["model"]
    
    # 5. Segment with Cellpose
    seg_result = await live_server.call_tool("run", {
        "fn_id": "cellpose.models.CellposeModel.eval",
        "inputs": {"model": model_ref, "x": intensity_ref},
        "params": {"diameter": 30.0}
    })
    labels_ref = seg_result["outputs"]["labels"]
    assert labels_ref["type"] == "LabelImageRef"
    
    # 6. Get mean lifetime
    lifetime_result = await live_server.call_tool("run", {
        "fn_id": "tttrlib.CLSMImage.get_mean_lifetime",
        "inputs": {"clsm": clsm_ref, "tttr_data": tttr_ref},
        "params": {"stack_frames": True}
    })
    lifetime_ref = lifetime_result["outputs"]["lifetime"]
    
    # 7. Compute per-cell statistics
    stats_result = await live_server.call_tool("run", {
        "fn_id": "base.skimage.measure.regionprops_table",
        "inputs": {"label_image": labels_ref, "intensity_image": lifetime_ref},
        "params": {"properties": ["label", "mean_intensity", "area"]}
    })
    assert stats_result["outputs"]["table"]["type"] == "TableRef"
```

## Implementation Checklist

### v0.2.0 Tasks

| Task ID | Description | Status |
|---------|-------------|--------|
| T-INT-01 | Add get_intensity schema to tttrlib_api.json | ⏳ Pending |
| T-INT-02 | Add get_intensity to manifest.yaml | ⏳ Pending |
| T-INT-03 | Write contract test for get_intensity | ⏳ Pending |
| T-INT-04 | Implement handle_get_intensity in entrypoint.py | ⏳ Pending |
| T-INT-05 | Write smoke test for intensity extraction | ⏳ Pending |
| T-PHA-01 | Add get_phasor schema to tttrlib_api.json | ⏳ Pending |
| T-PHA-02 | Add get_phasor to manifest.yaml | ⏳ Pending |
| T-PHA-03 | Write contract test for get_phasor | ⏳ Pending |
| T-PHA-04 | Implement handle_get_phasor in entrypoint.py | ⏳ Pending |
| T-PHA-05 | Write smoke test: Pathway A (get_phasor → phasorpy) | ⏳ Pending |
| T-DEC-01 | Add get_fluorescence_decay schema | ⏳ Pending |
| T-DEC-02 | Add get_fluorescence_decay to manifest | ⏳ Pending |
| T-DEC-03 | Implement handle_get_fluorescence_decay | ⏳ Pending |
| T-DEC-04 | Write smoke test: Pathway B (decay → phasor_from_signal) | ⏳ Pending |
| T-PRE-00 | Align schema/manifest drift (v0.1.0) | ⏳ Pending |
| T-REG-01 | Register all new handlers in FUNCTION_HANDLERS | ⏳ Pending |
| T-DOC-01 | Update quickstart.md with new workflows | ⏳ Pending |

### v0.3.0 Tasks

| Task ID | Description | Status |
|---------|-------------|--------|
| T-LIF-01 | Add get_mean_lifetime schema | ⏳ Pending |
| T-LIF-02 | Add get_mean_lifetime to manifest | ⏳ Pending |
| T-LIF-03 | Implement handle_get_mean_lifetime | ⏳ Pending |
| T-LIF-04 | Write smoke test for lifetime extraction | ⏳ Pending |
| T-CEL-01 | Write smoke test: tttrlib → Cellpose workflow | ⏳ Pending |
| T-CEL-02 | Verify axis compatibility between tools | ⏳ Pending |
| T-DOC-02 | Update quickstart.md with Cellpose workflow | ⏳ Pending |

## Risk Mitigation

### Potential Issues

1. **Axis ordering mismatch**: tttrlib uses (Z,Y,X) but Cellpose expects (Y,X) or (Z,Y,X)
   - **Mitigation**: `stack_frames=True` parameter to collapse frames (Z→YX)

2. **Phasor channel access**: PhasorPy expects separate g,s arrays but we output 4D
   - **Mitigation**: Either split in tttrlib handler or add base.xarray.isel support

3. **Memory pressure**: Large FLIM stacks with decay histograms
   - **Mitigation**: `micro_time_coarsening` parameter to reduce bins

4. **IRF handling**: Different tools expect different IRF formats
   - **Mitigation**: Use TTTRRef consistently; pass as `tttr_data`/`tttr_irf` per upstream tttrlib API

## Timeline Estimate

| Milestone | Phase | Estimated Duration |
|-----------|-------|-------------------|
| v0.2.0 | Phase 1: get_intensity | 2 days |
| v0.2.0 | Phase 2: get_phasor | 3 days |
| v0.2.0 | Phase 3: get_fluorescence_decay | 2 days |
| v0.2.0 | Integration tests + docs | 2 days |
| v0.3.0 | Phase 4: get_mean_lifetime | 2 days |
| v0.3.0 | Phase 5: Cellpose workflow | 3 days |
| v0.3.0 | End-to-end testing | 2 days |

**Total**: ~16 days

---

**Author**: AI Analysis  
**Date**: 2026-01-15  
**Status**: Implementation Plan Draft