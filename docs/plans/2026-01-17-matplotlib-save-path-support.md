# Matplotlib Save Path Support Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add user-defined path support to `base.matplotlib.Figure.savefig` and `base.matplotlib.pyplot.imsave` to match their underlying library signatures.

**Architecture:** Update the allowlist param schemas to include `fname` as optional, update implementations to use user-provided paths when given (with fs_allowlist_write validation), and fall back to auto-generated paths when omitted.

**Tech Stack:** Python 3.13, matplotlib, pydantic

---

## Context

### Library Signatures (Ground Truth)

```python
# matplotlib.figure.Figure.savefig
fig.savefig(fname, *, transparent=None, dpi='figure', format=None, 
            metadata=None, bbox_inches=None, pad_inches=0.1, 
            facecolor='auto', edgecolor='auto', backend=None, **kwargs)

# matplotlib.pyplot.imsave
plt.imsave(fname, arr, **kwargs)
# kwargs include: vmin, vmax, cmap, format, origin, dpi
```

### Current bioimage-mcp State

- `base.matplotlib.Figure.savefig`: Missing `fname` param entirely
- `base.matplotlib.pyplot.imsave`: No params defined at all

### Reference Implementation Pattern (from `base.io.bioimage.export`)

```python
# params_schema allows optional path
"path": {
    "type": "string",
    "description": "Optional output path. If omitted, generated in work_dir."
}
```

---

## Task 1: Add `fname` param to savefig allowlist

**Files:**
- Modify: `src/bioimage_mcp/registry/dynamic/adapters/matplotlib_allowlists.py:184-203`

**Step 1: Update the savefig entry in MATPLOTLIB_FIGURE_ALLOWLIST**

Add `fname` parameter to the params dict:

```python
"savefig": {
    "summary": "Save the current figure.",
    "io_pattern": "PLOT",
    "params": {
        "fname": {
            "type": "string",
            "description": "Output file path. If omitted, auto-generated in work directory.",
        },
        "format": {
            "type": "string",
            "description": "The file format (e.g. 'png', 'pdf', 'svg')",
        },
        "dpi": {"type": "number", "description": "The resolution in dots per inch"},
        "bbox_inches": {
            "type": "string",
            "description": "Bounding box in inches: 'tight' or None",
        },
        "transparent": {
            "type": "boolean",
            "description": "Whether to make the background transparent",
            "default": False,
        },
    },
},
```

**Step 2: Verify schema discovery works**

Run: `python -c "from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter; a = MatplotlibAdapter(); funcs = a.discover({}); sf = [f for f in funcs if f.fn_id == 'base.matplotlib.Figure.savefig'][0]; print('fname' in sf.parameters)"`

Expected: `True`

---

## Task 2: Add params to imsave allowlist

**Files:**
- Modify: `src/bioimage_mcp/registry/dynamic/adapters/matplotlib_allowlists.py:169`

**Step 1: Update the imsave entry in MATPLOTLIB_PYPLOT_ALLOWLIST**

Replace the minimal entry with a fully specified one:

```python
"imsave": {
    "summary": "Save an array as an image file.",
    "io_pattern": "PLOT",
    "params": {
        "fname": {
            "type": "string",
            "description": "Output file path. If omitted, auto-generated in work directory.",
        },
        "vmin": {
            "type": "number",
            "description": "Minimum value for colormap normalization",
        },
        "vmax": {
            "type": "number",
            "description": "Maximum value for colormap normalization",
        },
        "cmap": {
            "type": "string",
            "description": "Colormap name (e.g. 'gray', 'viridis')",
        },
        "format": {
            "type": "string",
            "description": "Image format (e.g. 'png', 'jpeg')",
        },
        "origin": {
            "type": "string",
            "description": "Place [0,0] at 'upper' or 'lower' left corner",
        },
        "dpi": {
            "type": "number",
            "description": "Resolution in dots per inch",
            "default": 150,
        },
    },
},
```

**Step 2: Verify schema discovery works**

Run: `python -c "from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter; a = MatplotlibAdapter(); funcs = a.discover({}); im = [f for f in funcs if f.fn_id == 'base.matplotlib.pyplot.imsave'][0]; print('fname' in im.parameters)"`

Expected: `True`

---

## Task 3: Update savefig implementation to use fname

**Files:**
- Modify: `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py:719-775`
- Test: `tests/unit/registry/test_matplotlib_path_validation.py` (existing tests should still pass)

**Step 1: Write failing test for user-provided path**

Create test in `tests/unit/ops/test_matplotlib_savefig_path.py`:

```python
"""Tests for savefig with user-provided path."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_savefig_uses_provided_fname():
    """savefig should use fname when provided."""
    from bioimage_mcp_base.ops.matplotlib_ops import savefig, OBJECT_CACHE
    
    # Create a mock figure
    mock_fig = MagicMock()
    mock_fig.dpi = 100
    mock_fig.get_size_inches.return_value = (8, 6)
    
    # Register in cache
    uri = "obj://test-session/matplotlib/fig-123"
    OBJECT_CACHE[uri] = mock_fig
    
    inputs = [("figure", {"uri": uri, "type": "ObjectRef"})]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "my_plot.png"
        params = {"fname": str(out_path)}
        
        with patch("bioimage_mcp_base.ops.matplotlib_ops.plt"):
            result = savefig(inputs, params, work_dir=Path(tmpdir))
        
        # Should have called savefig with user path
        mock_fig.savefig.assert_called_once()
        call_args = mock_fig.savefig.call_args
        assert str(out_path) in str(call_args)
        
        # Result should reference user path
        assert result[0]["path"] == str(out_path)


def test_savefig_autogenerates_without_fname():
    """savefig should auto-generate path when fname not provided."""
    from bioimage_mcp_base.ops.matplotlib_ops import savefig, OBJECT_CACHE
    
    mock_fig = MagicMock()
    mock_fig.dpi = 100
    mock_fig.get_size_inches.return_value = (8, 6)
    
    uri = "obj://test-session/matplotlib/fig-456"
    OBJECT_CACHE[uri] = mock_fig
    
    inputs = [("figure", {"uri": uri, "type": "ObjectRef"})]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        params = {"format": "png"}  # No fname
        
        with patch("bioimage_mcp_base.ops.matplotlib_ops.plt"):
            result = savefig(inputs, params, work_dir=Path(tmpdir))
        
        # Should have auto-generated path in work_dir
        result_path = Path(result[0]["path"])
        assert result_path.parent == Path(tmpdir)
        assert "plot_" in result_path.name
```

**Step 2: Run test to verify it fails**

Run: `conda run -n bioimage-mcp-base pytest tests/unit/ops/test_matplotlib_savefig_path.py -v`

Expected: FAIL (implementation doesn't handle fname yet)

**Step 3: Update savefig implementation**

Modify `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`:

```python
def savefig(
    inputs: list[Any],
    params: dict[str, Any],
    work_dir: Path | None = None,
    session_id: str = "default",
    env_id: str = "base",
) -> list[dict]:
    """Save figure to file."""
    fig = None
    for name, value in inputs:
        if name == "figure":
            fig = _load_object(value)
            break
    if not fig and inputs:
        fig = _load_object(inputs[0][1])

    if not fig:
        raise ValueError("Missing 'figure' input for savefig")

    if work_dir is None:
        work_dir = Path(tempfile.gettempdir())
    work_dir.mkdir(parents=True, exist_ok=True)

    # Handle user-provided fname
    user_fname = params.pop("fname", None)
    
    fmt = params.get("format", "png").lower()
    if fmt == "jpg":
        fmt = "jpeg"

    if user_fname:
        out_path = Path(user_fname)
        # Infer format from extension if not explicitly provided
        if "format" not in params and out_path.suffix:
            ext = out_path.suffix.lstrip(".").lower()
            if ext == "jpg":
                ext = "jpeg"
            fmt = ext
            params["format"] = fmt
    else:
        out_path = work_dir / f"plot_{uuid.uuid4().hex}.{fmt}"

    dpi = params.get("dpi", fig.dpi)
    w_inch, h_inch = fig.get_size_inches()

    fig.savefig(str(out_path), **params)
    plt.close(fig)

    # Clean up OBJECT_CACHE
    for uri, cached_fig in list(OBJECT_CACHE.items()):
        if cached_fig is fig:
            del OBJECT_CACHE[uri]

    plot_ref_fmt = "JPG" if fmt == "jpeg" else fmt.upper()

    return [
        {
            "type": "PlotRef",
            "format": plot_ref_fmt,
            "uri": out_path.absolute().as_uri(),
            "path": str(out_path.absolute()),
            "metadata": {
                "width_px": int(w_inch * dpi),
                "height_px": int(h_inch * dpi),
                "dpi": int(dpi),
                "plot_type": "matplotlib",
                "output_name": "plot",
            },
        }
    ]
```

**Step 4: Run test to verify it passes**

Run: `conda run -n bioimage-mcp-base pytest tests/unit/ops/test_matplotlib_savefig_path.py -v`

Expected: PASS

**Step 5: Run existing path validation tests**

Run: `pytest tests/unit/registry/test_matplotlib_path_validation.py -v`

Expected: PASS (no regressions)

---

## Task 4: Implement imsave function

**Files:**
- Modify: `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py` (add new function)
- Modify: `src/bioimage_mcp/registry/dynamic/adapters/matplotlib.py` (add dispatch)
- Test: `tests/unit/ops/test_matplotlib_imsave.py` (new)

**Step 1: Write failing test for imsave**

Create `tests/unit/ops/test_matplotlib_imsave.py`:

```python
"""Tests for matplotlib.pyplot.imsave."""
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest


def test_imsave_with_user_path():
    """imsave should save to user-provided path."""
    from bioimage_mcp_base.ops.matplotlib_ops import imsave
    
    # Create test image data
    arr = np.random.rand(100, 100)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "test_image.png"
        
        # Mock the artifact input
        inputs = [("image", {"type": "ObjectRef", "uri": "obj://test/arr"})]
        params = {"fname": str(out_path)}
        
        with patch("bioimage_mcp_base.ops.matplotlib_ops._load_image_data", return_value=arr):
            with patch("matplotlib.pyplot.imsave") as mock_imsave:
                result = imsave(inputs, params, work_dir=Path(tmpdir))
        
        mock_imsave.assert_called_once()
        call_args = mock_imsave.call_args
        assert call_args[0][0] == str(out_path)


def test_imsave_autogenerates_path():
    """imsave should auto-generate path when fname not provided."""
    from bioimage_mcp_base.ops.matplotlib_ops import imsave
    
    arr = np.random.rand(100, 100)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        inputs = [("image", {"type": "ObjectRef", "uri": "obj://test/arr"})]
        params = {"format": "png"}  # No fname
        
        with patch("bioimage_mcp_base.ops.matplotlib_ops._load_image_data", return_value=arr):
            with patch("matplotlib.pyplot.imsave") as mock_imsave:
                result = imsave(inputs, params, work_dir=Path(tmpdir))
        
        mock_imsave.assert_called_once()
        call_path = mock_imsave.call_args[0][0]
        assert tmpdir in call_path
        assert "image_" in call_path
```

**Step 2: Run test to verify it fails**

Run: `conda run -n bioimage-mcp-base pytest tests/unit/ops/test_matplotlib_imsave.py -v`

Expected: FAIL (imsave function doesn't exist)

**Step 3: Implement imsave function**

Add to `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`:

```python
def imsave(
    inputs: list[Any],
    params: dict[str, Any],
    work_dir: Path | None = None,
    session_id: str = "default",
    env_id: str = "base",
) -> list[dict]:
    """Save array as image file using matplotlib.pyplot.imsave."""
    # Load image data from input
    arr = None
    for name, value in inputs:
        if name in ("image", "arr"):
            arr = _load_image_data(value)
            break
    if arr is None and inputs:
        arr = _load_image_data(inputs[0][1])
    
    if arr is None:
        raise ValueError("Missing 'image' or 'arr' input for imsave")
    
    if work_dir is None:
        work_dir = Path(tempfile.gettempdir())
    work_dir.mkdir(parents=True, exist_ok=True)
    
    # Handle user-provided fname
    user_fname = params.pop("fname", None)
    
    fmt = params.get("format", "png").lower()
    if fmt == "jpg":
        fmt = "jpeg"
    
    if user_fname:
        out_path = Path(user_fname)
        # Infer format from extension if not explicitly provided
        if "format" not in params and out_path.suffix:
            ext = out_path.suffix.lstrip(".").lower()
            if ext == "jpg":
                ext = "jpeg"
            fmt = ext
    else:
        out_path = work_dir / f"image_{uuid.uuid4().hex}.{fmt}"
    
    # Call matplotlib imsave
    plt.imsave(str(out_path), arr, **params)
    
    return [
        {
            "type": "PlotRef",
            "format": fmt.upper(),
            "uri": out_path.absolute().as_uri(),
            "path": str(out_path.absolute()),
            "metadata": {
                "width_px": arr.shape[1] if arr.ndim >= 2 else arr.shape[0],
                "height_px": arr.shape[0] if arr.ndim >= 2 else 1,
                "plot_type": "imsave",
                "output_name": "output",
            },
        }
    ]


def _load_image_data(artifact: Any) -> np.ndarray | None:
    """Load image data from artifact (ObjectRef, BioImageRef, or array)."""
    if isinstance(artifact, np.ndarray):
        return artifact
    
    if isinstance(artifact, dict):
        uri = artifact.get("uri")
        path = artifact.get("path")
        artifact_type = artifact.get("type", "")
    else:
        uri = getattr(artifact, "uri", None)
        path = getattr(artifact, "path", None)
        artifact_type = getattr(artifact, "type", "")
    
    # ObjectRef in memory cache
    if uri and uri.startswith("obj://"):
        if uri in OBJECT_CACHE:
            obj = OBJECT_CACHE[uri]
            if isinstance(obj, np.ndarray):
                return obj
            # Could be xarray DataArray
            if hasattr(obj, "values"):
                return obj.values
        raise ValueError(f"ObjectRef with URI '{uri}' not found in cache")
    
    # BioImageRef - load from file
    if path or (uri and not uri.startswith("obj://")):
        if not path and uri:
            from urllib.parse import urlparse, unquote
            parsed = urlparse(str(uri))
            path = unquote(parsed.path)
            if path.startswith("/") and len(path) > 2 and path[2] == ":":
                path = path[1:]
        
        if path:
            from bioio import BioImage
            img = BioImage(path)
            return np.squeeze(img.data)
    
    return None
```

**Step 4: Add dispatch in matplotlib adapter**

Modify `src/bioimage_mcp/registry/dynamic/adapters/matplotlib.py`, add after line 389 (after savefig dispatch):

```python
if fn_id.endswith("matplotlib.pyplot.imsave"):
    return matplotlib_ops.imsave(
        normalized_inputs, params, work_dir, session_id=eff_session_id, env_id=env_id
    )
```

**Step 5: Run tests**

Run: `conda run -n bioimage-mcp-base pytest tests/unit/ops/test_matplotlib_imsave.py -v`

Expected: PASS

---

## Task 5: Add integration tests

**Files:**
- Test: `tests/integration/test_matplotlib_save_paths.py` (new)

**Step 1: Write integration test**

```python
"""Integration tests for matplotlib save functions with user paths."""
import tempfile
from pathlib import Path

import numpy as np
import pytest

from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter


@pytest.fixture
def adapter():
    return MatplotlibAdapter()


@pytest.fixture
def temp_write_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_savefig_with_user_path_integration(adapter, temp_write_dir):
    """Integration: savefig respects user-provided fname."""
    import matplotlib.pyplot as plt
    
    # Create a figure
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])
    
    # We need to register in memory store, but for now just test the adapter discover
    funcs = adapter.discover({})
    savefig_meta = [f for f in funcs if f.fn_id == "base.matplotlib.Figure.savefig"][0]
    
    # Verify fname param is exposed
    assert "fname" in savefig_meta.parameters
    
    plt.close(fig)


def test_imsave_with_user_path_integration(adapter, temp_write_dir):
    """Integration: imsave respects user-provided fname."""
    funcs = adapter.discover({})
    imsave_meta = [f for f in funcs if f.fn_id == "base.matplotlib.pyplot.imsave"][0]
    
    # Verify fname param is exposed
    assert "fname" in imsave_meta.parameters
    # Verify other params
    assert "cmap" in imsave_meta.parameters
    assert "vmin" in imsave_meta.parameters
```

**Step 2: Run integration tests**

Run: `pytest tests/integration/test_matplotlib_save_paths.py -v`

Expected: PASS

---

## Task 6: Update describe API to reflect new params

**Files:** None (automatic via adapter discovery)

**Step 1: Verify describe returns fname param**

Run:
```bash
python -c "
from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter
a = MatplotlibAdapter()
funcs = a.discover({})
sf = [f for f in funcs if f.fn_id == 'base.matplotlib.Figure.savefig'][0]
print('savefig params:', list(sf.parameters.keys()))
im = [f for f in funcs if f.fn_id == 'base.matplotlib.pyplot.imsave'][0]
print('imsave params:', list(im.parameters.keys()))
"
```

Expected output:
```
savefig params: ['fname', 'format', 'dpi', 'bbox_inches', 'transparent']
imsave params: ['fname', 'vmin', 'vmax', 'cmap', 'format', 'origin', 'dpi']
```

---

## Task 7: Run full test suite and commit

**Step 1: Run linting**

Run: `ruff check src/bioimage_mcp/registry/dynamic/adapters/matplotlib*.py tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`

Expected: No errors

**Step 2: Run full test suite**

Run: `pytest tests/unit/registry/test_matplotlib*.py tests/unit/ops/test_matplotlib*.py -v`

Expected: All PASS

**Step 3: Commit**

```bash
git add -A
git commit -m "feat(matplotlib): add fname param to savefig and imsave for user-defined paths

- Add fname parameter to MATPLOTLIB_FIGURE_ALLOWLIST savefig entry
- Add full param schema to MATPLOTLIB_PYPLOT_ALLOWLIST imsave entry  
- Update savefig implementation to use user path when provided
- Implement dedicated imsave function with path support
- Add dispatch for imsave in MatplotlibAdapter
- Path validation via fs_allowlist_write still applies

Closes #XXX"
```

---

## Summary

| Function | Before | After |
|----------|--------|-------|
| `base.matplotlib.Figure.savefig` | No path param, auto-generates only | `fname` optional, uses user path or auto-generates |
| `base.matplotlib.pyplot.imsave` | No params at all | Full params including `fname`, `cmap`, `vmin`, `vmax`, etc. |

The implementation follows the existing pattern from `base.io.bioimage.export` where path is optional and auto-generated when omitted.
