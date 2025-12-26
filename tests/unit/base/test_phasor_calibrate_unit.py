"""Unit tests for phasor_calibrate function."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))


def test_phasor_calibrate_basic(tmp_path: Path) -> None:
    """Test basic phasor calibration with synthetic data."""
    pytest.importorskip("phasorpy")

    from bioimage_mcp_base.transforms import phasor_calibrate

    # Create synthetic phasor data (2-channel: G in ch0, S in ch1)
    # For Fluorescein with τ=4.04ns at 80MHz: g ≈ 0.3, s ≈ 0.4
    sample_g = np.full((10, 10), 0.3, dtype=np.float32)
    sample_s = np.full((10, 10), 0.4, dtype=np.float32)
    sample_phasors = np.stack([sample_g, sample_s], axis=0)

    ref_g = np.full((10, 10), 0.3, dtype=np.float32)
    ref_s = np.full((10, 10), 0.4, dtype=np.float32)
    reference_phasors = np.stack([ref_g, ref_s], axis=0)

    # Save test data
    import tifffile

    sample_path = tmp_path / "sample_phasors.tif"
    ref_path = tmp_path / "reference_phasors.tif"
    tifffile.imwrite(str(sample_path), sample_phasors)
    tifffile.imwrite(str(ref_path), reference_phasors)

    # Call calibration
    work_dir = tmp_path / "output"
    work_dir.mkdir()

    result = phasor_calibrate(
        inputs={
            "sample_phasors": {"uri": f"file://{sample_path}", "type": "BioImageRef"},
            "reference_phasors": {"uri": f"file://{ref_path}", "type": "BioImageRef"},
        },
        params={
            "lifetime": 4.04,
            "frequency": 80e6,
            "harmonic": 1,
        },
        work_dir=work_dir,
    )

    assert result is not None
    assert "outputs" in result
    assert "calibrated_phasors" in result["outputs"]
    assert "provenance" in result

    # Verify provenance
    prov = result["provenance"]
    assert prov["reference_lifetime"] == 4.04
    assert prov["reference_frequency"] == 80e6
    assert prov["reference_harmonic"] == 1


def test_phasor_calibrate_rejects_negative_lifetime(tmp_path: Path) -> None:
    """Test that negative lifetime is rejected."""
    pytest.importorskip("phasorpy")

    from bioimage_mcp_base.transforms import phasor_calibrate

    # Create minimal test data
    phasors = np.zeros((2, 10, 10), dtype=np.float32)
    import tifffile

    sample_path = tmp_path / "sample.tif"
    ref_path = tmp_path / "ref.tif"
    tifffile.imwrite(str(sample_path), phasors)
    tifffile.imwrite(str(ref_path), phasors)

    work_dir = tmp_path / "output"
    work_dir.mkdir()

    with pytest.raises(ValueError, match="lifetime must be positive"):
        phasor_calibrate(
            inputs={
                "sample_phasors": {"uri": f"file://{sample_path}"},
                "reference_phasors": {"uri": f"file://{ref_path}"},
            },
            params={"lifetime": -1.0, "frequency": 80e6},
            work_dir=work_dir,
        )


def test_phasor_calibrate_rejects_invalid_channel_count(tmp_path: Path) -> None:
    """Test that non-2-channel input is rejected."""
    pytest.importorskip("phasorpy")

    from bioimage_mcp_base.transforms import phasor_calibrate

    # Create 3-channel data (invalid)
    phasors = np.zeros((3, 10, 10), dtype=np.float32)
    import tifffile

    sample_path = tmp_path / "sample.tif"
    ref_path = tmp_path / "ref.tif"
    tifffile.imwrite(str(sample_path), phasors)
    tifffile.imwrite(str(ref_path), np.zeros((2, 10, 10), dtype=np.float32))

    work_dir = tmp_path / "output"
    work_dir.mkdir()

    with pytest.raises(ValueError, match="Expected 2-channel phasor image"):
        phasor_calibrate(
            inputs={
                "sample_phasors": {"uri": f"file://{sample_path}"},
                "reference_phasors": {"uri": f"file://{ref_path}"},
            },
            params={"lifetime": 4.04, "frequency": 80e6},
            work_dir=work_dir,
        )
