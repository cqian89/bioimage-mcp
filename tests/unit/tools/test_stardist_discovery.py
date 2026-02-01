from __future__ import annotations

import sys
import pytest
from unittest.mock import MagicMock, patch
from bioimage_mcp_stardist.dynamic_discovery import StarDistAdapter
from bioimage_mcp.registry.dynamic.models import ParameterSchema, FunctionMetadata


def test_stardist_adapter_get_pretrained_model_names_mock():
    adapter = StarDistAdapter()

    # Mock the module in sys.modules so 'from csbdeep... import ...' works
    mock_pretrained = MagicMock()
    with patch.dict(
        sys.modules,
        {
            "csbdeep": MagicMock(),
            "csbdeep.models": MagicMock(),
            "csbdeep.models.pretrained": mock_pretrained,
        },
    ):
        mock_get = mock_pretrained.get_registered_models
        mock_get.return_value = (("model1", "model2"), {"alias": "model1"})

        names = adapter._get_pretrained_model_names(MagicMock())
        assert names == ["model1", "model2"]
        mock_get.assert_called_once()


def test_stardist_adapter_get_pretrained_model_names_import_error():
    adapter = StarDistAdapter()

    # Ensure csbdeep is NOT in sys.modules and will fail import
    with patch.dict(sys.modules, {}):
        if "csbdeep" in sys.modules:
            del sys.modules["csbdeep"]
        if "csbdeep.models.pretrained" in sys.modules:
            del sys.modules["csbdeep.models.pretrained"]

        names = adapter._get_pretrained_model_names(MagicMock())
        assert names == []


def test_stardist_adapter_discover_injects_enums():
    adapter = StarDistAdapter()

    # Mock model names return
    model_names = ["2D_versatile_fluo", "2D_versatile_he"]

    # Mock introspector to return a new meta object each time
    def mock_introspect(func, **kwargs):
        return FunctionMetadata(
            name="dummy",
            module="dummy",
            qualified_name="dummy",
            fn_id="dummy",
            source_adapter="stardist",
            description="dummy",
            parameters={
                "name": ParameterSchema(name="name", type="string", description="model name")
            },
        )

    adapter.introspector.introspect = MagicMock(side_effect=mock_introspect)

    with patch.object(adapter, "_get_pretrained_model_names", return_value=model_names):
        with patch.object(adapter, "_resolve_class", return_value=MagicMock()) as mock_resolve:
            metadata = adapter.discover({"prefix": "stardist"})

            # Filter for from_pretrained methods
            fp_metas = [m for m in metadata if "from_pretrained" in m.name]
            assert len(fp_metas) > 0

            for meta in fp_metas:
                assert "name" in meta.parameters
                assert meta.parameters["name"].enum == model_names
