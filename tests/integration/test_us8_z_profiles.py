from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from bioio import BioImage
from bioio.writers import OmeTiffWriter


@pytest.mark.integration
def test_z_stack_intensity_profile(mcp_test_client, tmp_path):
    """
    US8: Visualize Z-Stack Profiles (T039-T041)

    1. Create synthetic 3D Z-stack with known intensity profile.
    2. Compute mean intensity per Z-slice.
    3. Plot intensity vs Z-index.
    4. Label axes with physical units from metadata.
    """
    # 1. Create synthetic 3D data (Z=10, Y=64, X=64)
    # Intensity increases linearly with Z
    z_count = 10
    data = np.zeros((1, 1, z_count, 64, 64), dtype=np.float32)
    expected_means = []
    for z in range(z_count):
        intensity = 10.0 + z * 5.0
        data[0, 0, z, :, :] = intensity
        expected_means.append(intensity)

    # Save as TIFF with physical metadata
    img_path = tmp_path / "z_stack.ome.tiff"
    # bioio OmeTiffWriter expects (T, C, Z, Y, X)
    OmeTiffWriter.save(data, str(img_path), dim_order="TCZYX")

    # Verify metadata (Z physical size)
    # Note: bioio doesn't easily let us set physical pixel sizes in OmeTiffWriter.save
    # without a lot of boilerplate or using a template.
    # But we can check if it has a default or if we can mock/sim it.

    # 2. Use MCP tools to load and inspect
    load_res = mcp_test_client.call_tool("base.io.bioimage.load", {}, {"path": str(img_path)})
    assert load_res["status"] == "success"
    image_ref = load_res["outputs"]["image"]

    # 3. Compute mean intensity per Z-slice
    # For now, we do this in the test using numpy, as a "usage pattern"
    img = BioImage(img_path)
    # img.data is (T, C, Z, Y, X)
    pixel_data = img.data
    z_means = []
    for z in range(z_count):
        z_means.append(float(np.mean(pixel_data[0, 0, z, :, :])))

    assert np.allclose(z_means, expected_means)

    # 4. Create plot
    # a. Create subplots
    subplots_res = mcp_test_client.call_tool(
        "base.matplotlib.pyplot.subplots", {}, {"figsize": [8, 6]}
    )
    assert subplots_res["status"] == "success"
    fig_ref = next(out for out in subplots_res["outputs"].values() if out["type"] == "FigureRef")
    axes_ref = next(out for out in subplots_res["outputs"].values() if out["type"] == "AxesRef")

    # b. Plot Z-profile
    z_indices = list(range(z_count))

    # T041: Use physical units if available
    # We'll simulate physical units if bioio didn't save them (usually it doesn't by default)
    # But let's check what BioImage says
    z_spacing = 1.0
    z_unit = "slice"

    if img.physical_pixel_sizes.Z:
        z_spacing = img.physical_pixel_sizes.Z
        z_unit = "um"  # Assuming microns

    z_physical = [z * z_spacing for z in z_indices]

    plot_res = mcp_test_client.call_tool(
        "base.matplotlib.Axes.plot",
        {"axes": axes_ref},
        {"x": z_physical, "y": z_means, "fmt": "b-o", "label": "Mean Intensity"},
    )
    assert plot_res["status"] == "success"

    # c. Set labels
    xlabel = f"Z-position ({z_unit})"
    ylabel = "Mean Intensity (a.u.)"

    mcp_test_client.call_tool(
        "base.matplotlib.Axes.set_xlabel", {"axes": axes_ref}, {"xlabel": xlabel}
    )
    mcp_test_client.call_tool(
        "base.matplotlib.Axes.set_ylabel", {"axes": axes_ref}, {"ylabel": ylabel}
    )
    mcp_test_client.call_tool(
        "base.matplotlib.Axes.set_title", {"axes": axes_ref}, {"label": "Z-Stack Intensity Profile"}
    )
    mcp_test_client.call_tool("base.matplotlib.Axes.grid", {"axes": axes_ref}, {"visible": True})

    # d. Save figure
    save_res = mcp_test_client.call_tool(
        "base.matplotlib.Figure.savefig", {"figure": fig_ref}, {"format": "png"}
    )
    assert save_res["status"] == "success"
    plot_ref = save_res["outputs"]["plot"]

    plot_path = Path(plot_ref["uri"].replace("file://", ""))
    assert plot_path.exists()
    assert plot_ref["format"] == "PNG"
