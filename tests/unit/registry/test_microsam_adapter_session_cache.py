from unittest.mock import MagicMock, patch

import numpy as np

from bioimage_mcp.registry.dynamic.adapters.microsam import MicrosamAdapter
from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE


def test_microsam_adapter_cache_hit_miss_cycle(tmp_path):
    adapter = MicrosamAdapter()
    image_artifact = {
        "type": "BioImageRef",
        "uri": "file:///tmp/image.tif",
        "path": "/tmp/image.tif",
        "metadata": {"axes": "YX"},
    }
    image_data = np.zeros((10, 10), dtype=np.uint8)

    mock_util = MagicMock()
    mock_predictor = MagicMock()
    # predictor needs set_image method
    mock_predictor.set_image = MagicMock()
    mock_util.get_sam_model.return_value = mock_predictor

    with (
        patch.dict(
            "sys.modules",
            {
                "micro_sam": MagicMock(util=mock_util),
                "bioimage_mcp_microsam": MagicMock(),
                "bioimage_mcp_microsam.device": MagicMock(
                    select_device=MagicMock(return_value="cpu")
                ),
            },
        ),
        patch(
            "bioimage_mcp.registry.dynamic.adapters.microsam.MicrosamAdapter._load_image",
            return_value=image_data,
        ),
    ):
        # 1. First call: Cache MISS
        results = adapter.execute(
            fn_id="micro_sam.compute_embedding",
            inputs=[image_artifact],
            params={"model": "vit_b"},
            work_dir=tmp_path,
        )
        assert "MICROSAM_CACHE_MISS" in adapter.warnings
        assert "MICROSAM_CACHE_HIT" not in adapter.warnings
        assert len(results) == 1
        ref_id = results[0]["ref_id"]

        # 2. Second call: Cache HIT
        adapter.warnings = []
        results2 = adapter.execute(
            fn_id="micro_sam.compute_embedding",
            inputs=[image_artifact],
            params={"model": "vit_b"},
            work_dir=tmp_path,
        )
        assert "MICROSAM_CACHE_HIT" in adapter.warnings
        assert len(results2) == 1
        assert results2[0]["ref_id"] == ref_id

        # 3. Force fresh: Cache RESET
        adapter.warnings = []
        results3 = adapter.execute(
            fn_id="micro_sam.compute_embedding",
            inputs=[image_artifact],
            params={"model": "vit_b", "force_fresh": True},
            work_dir=tmp_path,
        )
        assert "MICROSAM_CACHE_RESET" in adapter.warnings
        assert "MICROSAM_CACHE_MISS" in adapter.warnings
        assert len(results3) == 1
        assert results3[0]["ref_id"] != ref_id

        # 4. Clear cache: RESET
        adapter.warnings = []
        adapter.execute(fn_id="micro_sam.cache.clear", inputs=[], params={}, work_dir=tmp_path)
        assert "MICROSAM_CACHE_RESET" in adapter.warnings

        # Next call should be MISS
        adapter.warnings = []
        adapter.execute(
            fn_id="micro_sam.compute_embedding",
            inputs=[image_artifact],
            params={"model": "vit_b"},
            work_dir=tmp_path,
        )
        assert "MICROSAM_CACHE_MISS" in adapter.warnings


def test_microsam_adapter_cache_corruption_fallback(tmp_path):
    adapter = MicrosamAdapter()
    image_artifact = {"type": "BioImageRef", "uri": "file:///corrupt.tif"}
    image_data = np.zeros((10, 10), dtype=np.uint8)

    # Manually inject corrupt entry (wrong type)
    key = adapter._get_cache_key(image_artifact, "vit_b")
    OBJECT_CACHE.set(key, "not a predictor")

    mock_util = MagicMock()
    mock_predictor = MagicMock()
    mock_predictor.set_image = MagicMock()
    mock_util.get_sam_model.return_value = mock_predictor

    with (
        patch.dict(
            "sys.modules",
            {
                "micro_sam": MagicMock(util=mock_util),
                "bioimage_mcp_microsam": MagicMock(),
                "bioimage_mcp_microsam.device": MagicMock(
                    select_device=MagicMock(return_value="cpu")
                ),
            },
        ),
        patch(
            "bioimage_mcp.registry.dynamic.adapters.microsam.MicrosamAdapter._load_image",
            return_value=image_data,
        ),
    ):
        results = adapter.execute(
            fn_id="micro_sam.compute_embedding",
            inputs=[image_artifact],
            params={"model": "vit_b"},
            work_dir=tmp_path,
        )
        assert "MICROSAM_CACHE_CORRUPT" in adapter.warnings
        assert "MICROSAM_CACHE_MISS" in adapter.warnings
        assert len(results) == 1


def test_microsam_adapter_amg_uses_cache(tmp_path):
    adapter = MicrosamAdapter()
    image_artifact = {
        "type": "BioImageRef",
        "uri": "file:///tmp/image_amg.tif",
        "path": "/tmp/image_amg.tif",
        "metadata": {"axes": "YX"},
    }
    image_data = np.zeros((10, 10), dtype=np.uint8)

    mock_util = MagicMock()
    mock_predictor = MagicMock()
    mock_predictor.set_image = MagicMock()
    mock_util.get_sam_model.return_value = mock_predictor

    mock_amg_class = MagicMock()
    mock_amg_instance = MagicMock()
    mock_amg_instance.generate.return_value = np.ones((10, 10), dtype=np.uint32)
    mock_amg_class.return_value = mock_amg_instance

    with (
        patch.dict(
            "sys.modules",
            {
                "micro_sam": MagicMock(util=mock_util),
                "micro_sam.instance_segmentation": MagicMock(AutomaticMaskGenerator=mock_amg_class),
                "bioimage_mcp_microsam": MagicMock(),
                "bioimage_mcp_microsam.device": MagicMock(
                    select_device=MagicMock(return_value="cpu")
                ),
            },
        ),
        patch(
            "bioimage_mcp.registry.dynamic.adapters.microsam.MicrosamAdapter._load_image",
            return_value=image_data,
        ),
        patch(
            "bioimage_mcp.registry.dynamic.adapters.microsam.MicrosamAdapter._save_image",
            return_value={"type": "LabelImageRef"},
        ),
    ):
        # First call: MISS
        adapter.execute(
            fn_id="micro_sam.instance_segmentation.automatic_mask_generator",
            inputs=[image_artifact],
            params={"model_type": "vit_b"},
            work_dir=tmp_path,
        )
        assert "MICROSAM_CACHE_MISS" in adapter.warnings

        # Second call: HIT
        adapter.warnings = []
        adapter.execute(
            fn_id="micro_sam.instance_segmentation.automatic_mask_generator",
            inputs=[image_artifact],
            params={"model_type": "vit_b"},
            work_dir=tmp_path,
        )
        assert "MICROSAM_CACHE_HIT" in adapter.warnings
