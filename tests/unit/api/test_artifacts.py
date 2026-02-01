from __future__ import annotations

import csv
import pickle
from pathlib import Path

import numpy as np
import tifffile

from bioimage_mcp.api.artifacts import ArtifactsService
from bioimage_mcp.artifacts.models import ObjectRef
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def test_artifacts_service_artifact_info(tmp_path: Path) -> None:
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )

    src = tmp_path / "test.txt"
    src.write_text("Hello World!")

    with ArtifactStore(config) as store:
        ref = store.import_file(src, artifact_type="LogRef", format="text")
        svc = ArtifactsService(store)

        # Test artifact_info with preview
        info = svc.artifact_info(ref.ref_id, text_preview_bytes=5)
        assert info["ref_id"] == ref.ref_id
        assert info["type"] == "LogRef"
        assert info["text_preview"] == "Hello"
        assert info["mime_type"] == "text/plain"
        assert len(info["checksums"]) > 0

        # Test artifact_info without preview
        info = svc.artifact_info(ref.ref_id)
        assert "text_preview" not in info

        # Test artifact_info not found
        info = svc.artifact_info("missing")
        assert info["error"]["code"] == "NOT_FOUND"


def test_artifact_info_objectref_native_type(tmp_path: Path) -> None:
    from bioimage_mcp.artifacts.models import ObjectRef

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[],
    )
    with ArtifactStore(config) as store:
        ref = ObjectRef(
            ref_id="obj1",
            uri="obj://session/env/obj1",
            storage_type="memory",
            python_class="test.module.TestClass",
        )
        # We manually put it in memory store for testing
        store._memory_store.register(ref)

        svc = ArtifactsService(store)
        info = svc.artifact_info("obj1")

        assert info["ref_id"] == "obj1"
        assert info["type"] == "ObjectRef"
        assert info["native_type"] == "test.module.TestClass"
        assert info["object_preview"] == "In-memory object (not serialized)"


def test_artifact_info_objectref_preview_truncation(tmp_path: Path) -> None:
    import pickle

    from bioimage_mcp.artifacts.models import ObjectRef

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[],
    )

    obj = "A" * 600
    sim_path = tmp_path / "obj.pkl"
    with open(sim_path, "wb") as f:
        pickle.dump(obj, f)

    with ArtifactStore(config) as store:
        ref = ObjectRef(
            ref_id="obj2",
            uri="obj://session/env/obj2",
            storage_type="memory",
            python_class="str",
            metadata={"_simulated_path": str(sim_path)},
        )
        store._memory_store.register(ref)

        svc = ArtifactsService(store)
        info = svc.artifact_info("obj2")

        assert "object_preview" in info
        assert len(info["object_preview"]) == 500
        assert info["object_preview"].endswith("...")


def test_artifact_info_objectref_expired(tmp_path: Path) -> None:
    from bioimage_mcp.artifacts.models import ObjectRef

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[],
    )

    with ArtifactStore(config) as store:
        # Path does not exist
        ref = ObjectRef(
            ref_id="expired",
            uri="obj://session/env/expired",
            storage_type="memory",
            python_class="str",
            metadata={"_simulated_path": str(tmp_path / "missing.pkl")},
        )
        store._memory_store.register(ref)

        svc = ArtifactsService(store)
        info = svc.artifact_info("expired")

        assert info["error"]["code"] == "OBJECT_REF_EXPIRED"


def test_artifact_info_label_image_preview(tmp_path: Path) -> None:
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )

    # Create a small label image
    label_img = np.zeros((10, 10), dtype=np.uint16)
    label_img[2:5, 2:5] = 1
    label_path = tmp_path / "labels.ome.tif"
    tifffile.imwrite(label_path, label_img, ome=True)

    with ArtifactStore(config) as store:
        ref = store.import_file(
            label_path,
            artifact_type="LabelImageRef",
            format="ome-tiff",
            metadata_override={"dims": "YX", "shape": [10, 10], "dtype": "uint16", "ndim": 2},
        )
        svc = ArtifactsService(store)

        # Test with preview
        info = svc.artifact_info(ref.ref_id, include_image_preview=True)
        assert "image_preview" in info
        preview = info["image_preview"]
        assert "base64" in preview
        assert preview["region_count"] == 1
        assert len(preview["centroids"]) == 1


def test_artifact_info_table_preview(tmp_path: Path) -> None:
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )

    csv_path = tmp_path / "test.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["A", "B"])
        writer.writerow([1, 2])

    with ArtifactStore(config) as store:
        ref = store.import_file(
            csv_path,
            artifact_type="TableRef",
            format="csv",
            metadata_override={
                "columns": [{"name": "A", "dtype": "int64"}, {"name": "B", "dtype": "string"}]
            },
        )
        svc = ArtifactsService(store)

        # Test with preview
        info = svc.artifact_info(ref.ref_id, include_table_preview=True)
        assert "table_preview" in info
        assert "dtypes" in info
        assert info["dtypes"]["A"] == "int64"
        assert info["total_rows"] is not None


def test_artifact_info_plot_preview(tmp_path: Path) -> None:
    from PIL import Image

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
    )

    # 1. Create a 500x300 PNG plot
    plot_path = tmp_path / "plot.png"
    img = Image.new("RGB", (500, 300), color="red")
    img.save(plot_path)

    with ArtifactStore(config) as store:
        # 2. Import as PlotRef
        ref = store.import_file(
            plot_path,
            artifact_type="PlotRef",
            format="PNG",
            metadata_override={"width_px": 500, "height_px": 300, "dpi": 72},
        )
        svc = ArtifactsService(store)

        # 3. Request preview with 128px cap
        info = svc.artifact_info(ref.ref_id, include_image_preview=True, image_preview_size=128)

        assert "image_preview" in info
        preview = info["image_preview"]
        assert preview["format"] == "png"
        assert preview["width"] == 128
        assert preview["height"] == int(300 * (128 / 500))
        assert "base64" in preview

        # 4. Test SVG preview
        svg_path = tmp_path / "plot.svg"
        svg_path.write_text(
            '<svg width="1000" height="500"><rect width="100" height="100" fill="blue"/></svg>'
        )

        ref_svg = store.import_file(
            svg_path,
            artifact_type="PlotRef",
            format="SVG",
            metadata_override={"width_px": 1000, "height_px": 500},
        )

        info_svg = svc.artifact_info(
            ref_svg.ref_id, include_image_preview=True, image_preview_size=256
        )
        assert info_svg["image_preview"]["format"] == "svg"
        assert info_svg["image_preview"]["width"] == 256
        assert info_svg["image_preview"]["height"] == 128
