from __future__ import annotations

import base64
import pickle
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
import tifffile
from PIL import Image

from bioimage_mcp.api.artifacts import ArtifactsService
from bioimage_mcp.artifacts.models import ObjectRef


@pytest.fixture
def artifacts_service(mcp_services):
    return ArtifactsService(mcp_services["artifact_store"])


def create_tiff(path: Path, data: np.ndarray, axes: str = "YX"):
    # Simplified tiff creation for testing
    # Use ome=True for better bioio compatibility
    tifffile.imwrite(str(path), data, metadata={"axes": axes}, ome=True)


@pytest.mark.integration
@pytest.mark.requires_base
def test_bioimage_preview_2d(artifacts_service, tmp_path):
    img_path = tmp_path / "test_2d.tif"
    data = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
    create_tiff(img_path, data)

    ref = artifacts_service._store.import_file(
        img_path, artifact_type="BioImageRef", format="OME-TIFF"
    )
    info = artifacts_service.artifact_info(ref.ref_id, include_image_preview=True)

    assert "image_preview" in info
    preview = info["image_preview"]
    assert "base64" in preview
    assert preview["format"] == "png"

    # Verify it's a valid PNG
    img_data = base64.b64decode(preview["base64"])
    img = Image.open(BytesIO(img_data))
    assert img.size == (100, 100)
    assert img.mode in ("L", "RGB", "RGBA")


@pytest.mark.integration
@pytest.mark.requires_base
def test_bioimage_preview_3d_max_projection(artifacts_service, tmp_path):
    img_path = tmp_path / "test_3d.tif"
    # 10 slices of 100x100
    data = np.zeros((10, 100, 100), dtype=np.uint8)
    data[0, 10, 10] = 255
    data[5, 50, 50] = 255
    create_tiff(img_path, data, axes="ZYX")

    ref = artifacts_service._store.import_file(
        img_path, artifact_type="BioImageRef", format="OME-TIFF"
    )

    # Default is max projection
    info = artifacts_service.artifact_info(ref.ref_id, include_image_preview=True)
    img_data = base64.b64decode(info["image_preview"]["base64"])
    img = np.array(Image.open(BytesIO(img_data)))

    assert img[10, 10] > 0
    assert img[50, 50] > 0


@pytest.mark.integration
@pytest.mark.requires_base
def test_bioimage_preview_3d_mean_projection(artifacts_service, tmp_path):
    img_path = tmp_path / "test_3d_mean.tif"
    data = np.zeros((10, 100, 100), dtype=np.uint8)
    # Point 1: present in 2 slices
    data[0, 10, 10] = 255
    data[1, 10, 10] = 255
    # Point 2: present in 1 slice
    data[2, 20, 20] = 255
    create_tiff(img_path, data, axes="ZYX")

    ref = artifacts_service._store.import_file(
        img_path, artifact_type="BioImageRef", format="OME-TIFF"
    )

    info = artifacts_service.artifact_info(
        ref.ref_id, include_image_preview=True, projection="mean"
    )
    img_data = base64.b64decode(info["image_preview"]["base64"])
    img = np.array(Image.open(BytesIO(img_data)))

    # Point 1 should be brighter than Point 2
    assert img[10, 10] > img[20, 20]
    # Point 1 should be max (255) due to normalization
    assert img[10, 10] == 255
    # Point 2 should be roughly half (127)
    assert 120 < img[20, 20] < 135


@pytest.mark.integration
@pytest.mark.requires_base
def test_bioimage_preview_3d_slice(artifacts_service, tmp_path):
    img_path = tmp_path / "test_3d_slice.tif"
    data = np.zeros((10, 100, 100), dtype=np.uint8)
    data[5, 50, 50] = 255
    create_tiff(img_path, data, axes="ZYX")

    ref = artifacts_service._store.import_file(
        img_path, artifact_type="BioImageRef", format="OME-TIFF"
    )

    # Slice 5 should have the point
    info = artifacts_service.artifact_info(
        ref.ref_id, include_image_preview=True, projection="slice", slice_indices={"Z": 5}
    )
    img_data = base64.b64decode(info["image_preview"]["base64"])
    img = np.array(Image.open(BytesIO(img_data)))
    assert img[50, 50] == 255

    # Slice 0 should be empty
    info = artifacts_service.artifact_info(
        ref.ref_id, include_image_preview=True, projection="slice", slice_indices={"Z": 0}
    )
    img_data = base64.b64decode(info["image_preview"]["base64"])
    img = np.array(Image.open(BytesIO(img_data)))
    assert img[50, 50] == 0


@pytest.mark.integration
@pytest.mark.requires_base
def test_bioimage_preview_5d_reduction(artifacts_service, tmp_path):
    img_path = tmp_path / "test_5d.tif"
    # T=2, C=3, Z=5, Y=20, X=20
    data = np.zeros((2, 3, 5, 20, 20), dtype=np.uint8)
    # Put point at C=0 because default preview takes first channel
    data[1, 0, 1, 10, 10] = 255
    # Write as OME-TIFF to ensure dimensions are correctly identified
    tifffile.imwrite(str(img_path), data, metadata={"axes": "TCZYX"}, ome=True)

    ref = artifacts_service._store.import_file(
        img_path, artifact_type="BioImageRef", format="OME-TIFF"
    )

    # Max projection across all but YX
    info = artifacts_service.artifact_info(ref.ref_id, include_image_preview=True)
    assert "image_preview" in info
    img_data = base64.b64decode(info["image_preview"]["base64"])
    img = np.array(Image.open(BytesIO(img_data)))
    # Should find the bright spot
    assert np.max(img) > 200


@pytest.mark.integration
@pytest.mark.requires_base
def test_bioimage_preview_size_limit(artifacts_service, tmp_path):
    img_path = tmp_path / "test_large.tif"
    data = np.zeros((1000, 1000), dtype=np.uint8)
    create_tiff(img_path, data)

    ref = artifacts_service._store.import_file(
        img_path, artifact_type="BioImageRef", format="OME-TIFF"
    )

    # Default limit is 256
    info = artifacts_service.artifact_info(ref.ref_id, include_image_preview=True)
    img_data = base64.b64decode(info["image_preview"]["base64"])
    img = Image.open(BytesIO(img_data))
    assert max(img.size) == 256

    # Custom limit
    info = artifacts_service.artifact_info(
        ref.ref_id, include_image_preview=True, image_preview_size=128
    )
    img_data = base64.b64decode(info["image_preview"]["base64"])
    img = Image.open(BytesIO(img_data))
    assert max(img.size) == 128


@pytest.mark.integration
@pytest.mark.requires_base
def test_bioimage_preview_channel_selection(artifacts_service, tmp_path):
    img_path = tmp_path / "test_channels.tif"
    data = np.zeros((3, 100, 100), dtype=np.uint8)
    data[0, 10, 10] = 255  # Red (if RGB)
    data[1, 20, 20] = 255  # Green
    data[2, 30, 30] = 255  # Blue
    create_tiff(img_path, data, axes="CYX")

    ref = artifacts_service._store.import_file(
        img_path, artifact_type="BioImageRef", format="OME-TIFF"
    )

    # Channel 1 (Green)
    info = artifacts_service.artifact_info(ref.ref_id, include_image_preview=True, channels=1)
    img_data = base64.b64decode(info["image_preview"]["base64"])
    img = np.array(Image.open(BytesIO(img_data)))
    assert img[20, 20] == 255
    assert img[10, 10] == 0
    assert img[30, 30] == 0


@pytest.mark.integration
@pytest.mark.requires_base
def test_bioimage_preview_omitted_on_failure(artifacts_service, tmp_path):
    # Create a non-image file but call it an image
    bogus_path = tmp_path / "bogus.tif"
    bogus_path.write_text("not an image")

    ref = artifacts_service._store.import_file(
        bogus_path, artifact_type="BioImageRef", format="OME-TIFF"
    )

    # Should not crash, just omit image_preview
    info = artifacts_service.artifact_info(ref.ref_id, include_image_preview=True)
    assert "image_preview" not in info


@pytest.mark.integration
@pytest.mark.requires_base
def test_label_preview_colormap(artifacts_service, tmp_path):
    label_path = tmp_path / "labels.tif"
    data = np.zeros((100, 100), dtype=np.uint16)
    data[10:20, 10:20] = 1
    data[50:60, 50:60] = 2
    create_tiff(label_path, data)

    ref = artifacts_service._store.import_file(
        label_path, artifact_type="LabelImageRef", format="OME-TIFF"
    )
    info = artifacts_service.artifact_info(ref.ref_id, include_image_preview=True)

    assert "image_preview" in info
    img_data = base64.b64decode(info["image_preview"]["base64"])
    img = Image.open(BytesIO(img_data))

    # Label image previews should be RGBA
    assert img.mode == "RGBA"

    # Labels should have different colors
    pix = np.array(img)
    c1 = pix[15, 15]
    c2 = pix[55, 55]
    c0 = pix[0, 0]

    assert c1[3] == 255  # Opaque
    assert c2[3] == 255  # Opaque
    assert c0[3] == 0  # Transparent background
    assert not np.array_equal(c1, c2)


@pytest.mark.integration
@pytest.mark.requires_base
def test_label_preview_region_count(artifacts_service, tmp_path):
    label_path = tmp_path / "labels_count.tif"
    data = np.zeros((100, 100), dtype=np.uint16)
    data[10:20, 10:20] = 1
    data[50:60, 50:60] = 2
    data[80:90, 80:90] = 5  # skip 3, 4
    create_tiff(label_path, data)

    ref = artifacts_service._store.import_file(
        label_path, artifact_type="LabelImageRef", format="OME-TIFF"
    )
    info = artifacts_service.artifact_info(ref.ref_id, include_image_preview=True)

    assert "image_preview" in info
    preview = info["image_preview"]
    assert preview.get("region_count") == 3


@pytest.mark.integration
@pytest.mark.requires_base
def test_label_preview_centroids(artifacts_service, tmp_path):
    label_path = tmp_path / "labels_centroids.tif"
    data = np.zeros((100, 100), dtype=np.uint16)
    data[10:20, 10:20] = 1
    create_tiff(label_path, data)

    ref = artifacts_service._store.import_file(
        label_path, artifact_type="LabelImageRef", format="OME-TIFF"
    )
    info = artifacts_service.artifact_info(ref.ref_id, include_image_preview=True)

    preview = info["image_preview"]
    centroids = preview.get("centroids", [])
    assert len(centroids) == 1
    c = centroids[0]
    # y, x center of 10-19 is 14.5
    assert 14 <= c[0] <= 15
    assert 14 <= c[1] <= 15


@pytest.mark.integration
@pytest.mark.requires_base
def test_label_preview_empty_labels(artifacts_service, tmp_path):
    label_path = tmp_path / "empty_labels.tif"
    data = np.zeros((100, 100), dtype=np.uint16)
    create_tiff(label_path, data)

    ref = artifacts_service._store.import_file(
        label_path, artifact_type="LabelImageRef", format="OME-TIFF"
    )
    info = artifacts_service.artifact_info(ref.ref_id, include_image_preview=True)

    assert "image_preview" in info
    preview = info["image_preview"]
    assert preview.get("region_count") == 0
    assert preview.get("centroids") == []


@pytest.mark.integration
def test_table_preview_markdown(artifacts_service, tmp_path):
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("A,B,C\n1,2,3\n4,5,6")

    ref = artifacts_service._store.import_file(csv_path, artifact_type="TableRef", format="CSV")
    info = artifacts_service.artifact_info(ref.ref_id, include_table_preview=True)

    assert "table_preview" in info
    assert "| A | B | C |" in info["table_preview"]
    assert "| 1 | 2 | 3 |" in info["table_preview"]


@pytest.mark.integration
def test_table_preview_dtypes(artifacts_service, tmp_path):
    csv_path = tmp_path / "test_dtypes.csv"
    csv_path.write_text("name,age,score\nalice,30,95.5\nbob,25,88.0")

    ref = artifacts_service._store.import_file(csv_path, artifact_type="TableRef", format="CSV")
    info = artifacts_service.artifact_info(ref.ref_id, include_table_preview=True)

    assert "dtypes" in info
    dtypes = info["dtypes"]
    assert "name" in dtypes
    assert "age" in dtypes
    assert "score" in dtypes


@pytest.mark.integration
def test_table_preview_row_limit(artifacts_service, tmp_path):
    csv_path = tmp_path / "test_rows.csv"
    lines = ["A,B"] + [f"{i},{i * 2}" for i in range(20)]
    csv_path.write_text("\n".join(lines))

    ref = artifacts_service._store.import_file(csv_path, artifact_type="TableRef", format="CSV")

    # Default 5 rows
    info = artifacts_service.artifact_info(ref.ref_id, include_table_preview=True)
    rows = [line for line in info["table_preview"].split("\n") if line.strip() and "-" not in line]
    # Header + 5 rows = 6 lines
    assert len(rows) == 6

    # Custom 10 rows
    info = artifacts_service.artifact_info(ref.ref_id, include_table_preview=True, preview_rows=10)
    rows = [line for line in info["table_preview"].split("\n") if line.strip() and "-" not in line]
    assert len(rows) == 11


@pytest.mark.integration
def test_table_preview_column_limit(artifacts_service, tmp_path):
    csv_path = tmp_path / "test_cols.csv"
    header = ",".join([f"col_{i}" for i in range(10)])
    row = ",".join([str(i) for i in range(10)])
    csv_path.write_text(f"{header}\n{row}")

    ref = artifacts_service._store.import_file(csv_path, artifact_type="TableRef", format="CSV")

    # Limit to 3 columns
    info = artifacts_service.artifact_info(
        ref.ref_id, include_table_preview=True, preview_columns=3
    )
    header_line = info["table_preview"].split("\n")[0]
    assert "| col_0 | col_1 | col_2 |" in header_line
    assert "col_3" not in header_line


@pytest.mark.integration
def test_table_preview_counts(artifacts_service, tmp_path):
    csv_path = tmp_path / "test_counts.csv"
    csv_path.write_text("A,B,C\n1,2,3\n4,5,6\n7,8,9")

    ref = artifacts_service._store.import_file(csv_path, artifact_type="TableRef", format="CSV")
    info = artifacts_service.artifact_info(ref.ref_id)

    assert info["total_rows"] == 3
    assert info["total_columns"] == 3


@pytest.mark.integration
def test_objectref_native_type(artifacts_service):
    ref_id = "obj_123"
    ref = ObjectRef(
        ref_id=ref_id,
        uri=f"obj://sess1/env1/{ref_id}",
        storage_type="memory",
        python_class="dict",
        metadata={},
    )
    artifacts_service._store._memory_store.register(ref)

    info = artifacts_service.artifact_info(ref_id)
    assert info["native_type"] == "dict"


@pytest.mark.integration
def test_objectref_preview_truncation(artifacts_service, tmp_path):
    # Long object
    obj = "x" * 1000
    sim_path = tmp_path / "obj.pkl"
    with open(sim_path, "wb") as f:
        pickle.dump(obj, f)

    ref_id = "obj_long"
    ref = ObjectRef(
        ref_id=ref_id,
        uri=f"obj://sess1/env1/{ref_id}",
        storage_type="memory",
        python_class="str",
        metadata={"_simulated_path": str(sim_path)},
    )
    artifacts_service._store._memory_store.register(ref)

    info = artifacts_service.artifact_info(ref_id)
    assert "object_preview" in info
    preview = info["object_preview"]
    assert len(preview) <= 500
    assert preview.endswith("...")
