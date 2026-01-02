"""Standalone integration test for Cellpose in bioimage-mcp-cellpose environment.

This test validates that:
1. Cellpose can segment images correctly
2. The run_segment function works end-to-end
3. Output artifacts are generated correctly

Run with: conda run -n bioimage-mcp-cellpose python /tmp/test_cellpose_standalone.py
"""

import sys
import tempfile
from pathlib import Path

# Add the tools/cellpose package to path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools/cellpose"))
# Fallback for running from project root
sys.path.insert(0, "tools/cellpose")

import numpy as np
import tifffile


def create_synthetic_cell_image(size=256, n_cells=5, cell_radius=25):
    """Create a synthetic image with cell-like circles."""
    img = np.zeros((size, size), dtype=np.float32)
    np.random.seed(42)
    
    for i in range(n_cells):
        cx = np.random.randint(cell_radius + 10, size - cell_radius - 10)
        cy = np.random.randint(cell_radius + 10, size - cell_radius - 10)
        r = cell_radius + np.random.randint(-5, 5)
        
        y, x = np.ogrid[:size, :size]
        mask = (x - cx)**2 + (y - cy)**2 <= r**2
        img[mask] = 1.0 + np.random.rand() * 0.5
    
    # Add noise
    img += np.random.rand(size, size) * 0.1
    return img


def test_cellpose_direct_execution():
    """Test that cellpose can segment a synthetic image directly."""
    print("Test 1: Direct cellpose execution...")
    
    from cellpose.models import CellposeModel
    
    img = create_synthetic_cell_image()
    model = CellposeModel(model_type='cyto3')
    masks, flows, styles = model.eval(img, diameter=50, channels=[0, 0])
    
    n_cells = masks.max()
    assert n_cells > 0, f"Expected cells, got {n_cells}"
    print(f"  ✓ Found {n_cells} cells in synthetic image")


def test_run_segment_function():
    """Test the run_segment function from bioimage_mcp_cellpose."""
    print("Test 2: run_segment function...")
    
    from bioimage_mcp_cellpose.ops.segment import run_segment
    
    # Create temporary input image
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create and save synthetic image
        img = create_synthetic_cell_image()
        input_path = tmpdir / "input.tif"
        tifffile.imwrite(str(input_path), img)
        
        # Create work directory
        work_dir = tmpdir / "work"
        work_dir.mkdir()
        
        # Create input artifact reference
        inputs = {
            "image": {
                "uri": f"file://{input_path.absolute()}",
                "format": "TIFF",  # Use plain TIFF to avoid OME parsing issues
            }
        }
        
        # Run segmentation
        params = {"model_type": "cyto3", "diameter": 50.0}
        result = run_segment(inputs, params, work_dir)
        
        # Verify outputs
        assert "labels" in result, "Missing labels output"
        labels_path = Path(result["labels"]["path"])
        assert labels_path.exists(), f"Labels file not found: {labels_path}"
        
        # Read and verify labels
        labels = tifffile.imread(str(labels_path))
        n_cells = labels.max()
        assert n_cells > 0, f"Expected cells in output, got {n_cells}"
        
        print(f"  ✓ run_segment produced {n_cells} cells")
        print(f"  ✓ Labels saved to: {labels_path}")


def test_output_artifacts():
    """Test that output artifacts have correct format."""
    print("Test 3: Output artifact format...")
    
    from bioimage_mcp_cellpose.ops.segment import run_segment
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        img = create_synthetic_cell_image()
        input_path = tmpdir / "input.tif"
        tifffile.imwrite(str(input_path), img)
        
        work_dir = tmpdir / "work"
        work_dir.mkdir()
        
        inputs = {
            "image": {
                "uri": f"file://{input_path.absolute()}",
                "format": "TIFF",
            }
        }
        
        result = run_segment(inputs, {"model_type": "cyto3", "diameter": 50.0}, work_dir)
        
        # Check labels artifact
        labels = result["labels"]
        assert labels["type"] == "LabelImageRef", f"Wrong type: {labels['type']}"
        assert labels["format"] == "OME-TIFF", f"Wrong format: {labels['format']}"
        
        # Check cellpose bundle artifact
        bundle = result.get("cellpose_bundle")
        if bundle:
            assert bundle["type"] == "NativeOutputRef"
            assert bundle["format"] == "cellpose-seg-npy"
        
        print("  ✓ Output artifacts have correct format")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Cellpose Integration Tests (bioimage-mcp-cellpose environment)")
    print("=" * 60)
    
    tests = [
        test_cellpose_direct_execution,
        test_run_segment_function,
        test_output_artifacts,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
