from __future__ import annotations

import numpy as np
import pytest
from pathlib import Path

# Integration tests for trackpy adapter execution in trackpy env.
# These tests run INSIDE the trackpy environment via micromamba run.

# Skip if trackpy not installed (e.g. running in base server env)
tp = pytest.importorskip("trackpy")


@pytest.fixture
def synthetic_spots_image():
    """Generate a synthetic image with bright spots on dark background."""
    shape = (128, 128)
    data = np.zeros(shape, dtype=np.float32)

    # Define 5 spot centers
    centers = [(30, 30), (30, 90), (90, 30), (90, 90), (64, 64)]

    # Create spots
    for r, c in centers:
        rr, cc = np.ogrid[: shape[0], : shape[1]]
        # Small radius
        mask = (rr - r) ** 2 + (cc - c) ** 2 <= 2**2
        data[mask] = 1.0

    # Add Gaussian blur to simulate PSF
    from scipy.ndimage import gaussian_filter

    data = gaussian_filter(data, sigma=1.5)

    # Add some noise
    rng = np.random.default_rng(42)
    data += rng.normal(0, 0.05, shape)
    data = np.clip(data, 0, 1)

    # Convert to uint8 for typical processing
    return (data * 255).astype(np.uint8)


@pytest.mark.requires_env("bioimage-mcp-trackpy")
def test_library_locate_basic(synthetic_spots_image):
    """Verify trackpy library can locate synthetic spots."""
    diameter = 11
    # Run locate
    f = tp.locate(synthetic_spots_image, diameter, minmass=100)

    # Verify we found exactly 5 spots
    assert len(f) == 5, f"Expected 5 spots, found {len(f)}"

    # Verify standard columns exist
    expected_cols = {"x", "y", "mass", "size", "ecc", "signal", "raw_mass"}
    assert expected_cols.issubset(set(f.columns))

    # Verify coordinates are roughly correct (sorted by y, x)
    f_sorted = f.sort_values(["y", "x"]).reset_index(drop=True)
    # First spot at (30, 30)
    assert np.isclose(f_sorted.loc[0, "y"], 30, atol=1.5)
    assert np.isclose(f_sorted.loc[0, "x"], 30, atol=1.5)


@pytest.mark.requires_env("bioimage-mcp-trackpy")
def test_library_batch_and_link(synthetic_spots_image):
    """Verify trackpy library can batch locate and link trajectories."""
    diameter = 11
    # Create 3 frames (static)
    frames = [synthetic_spots_image] * 3

    # Batch locate
    f = tp.batch(frames, diameter, minmass=100)

    assert len(f) == 15  # 5 spots * 3 frames
    assert "frame" in f.columns
    assert f["frame"].nunique() == 3

    # Link trajectories
    # Since frames are identical, displacement is 0
    t = tp.link(f, search_range=5, memory=1)

    assert "particle" in t.columns
    # Should have exactly 5 particles
    assert t["particle"].nunique() == 5
    # Each particle should have 3 observations
    counts = t.groupby("particle").size()
    assert (counts == 3).all()


@pytest.mark.requires_env("bioimage-mcp-trackpy")
def test_library_filtering(synthetic_spots_image):
    """Verify trackpy filtering functions work."""
    diameter = 11
    f = tp.locate(synthetic_spots_image, diameter)

    # Filter by mass
    # All our synthetic spots have similar mass
    avg_mass = f["mass"].mean()
    f_filtered = f[f["mass"] > avg_mass * 0.8]

    assert len(f_filtered) == 5

    # Subpixel bias check (should not raise)
    tp.subpixel_bias(f)
