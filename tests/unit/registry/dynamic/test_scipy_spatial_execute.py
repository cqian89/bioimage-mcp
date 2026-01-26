import pytest
import numpy as np
import pandas as pd
import json
from unittest.mock import patch, MagicMock
from bioimage_mcp.registry.dynamic.adapters.scipy_spatial import ScipySpatialAdapter
from bioimage_mcp.registry.dynamic import object_cache


@pytest.fixture
def spatial_adapter():
    return ScipySpatialAdapter()


@pytest.mark.requires_base
def test_execute_cdist(spatial_adapter, tmp_path):
    df_a = pd.DataFrame({"x": [0.0, 1.0], "y": [0.0, 1.0]})
    df_b = pd.DataFrame({"x": [1.0, 0.0], "y": [1.0, 0.0]})

    uri_a = "obj://test/table_a"
    uri_b = "obj://test/table_b"
    object_cache.register(uri_a, df_a)
    object_cache.register(uri_b, df_b)

    inputs = [
        ("table_a", {"uri": uri_a, "type": "TableRef"}),
        ("table_b", {"uri": uri_b, "type": "TableRef"}),
    ]
    params = {"metric": "euclidean"}

    with patch("scipy.spatial.distance.cdist") as mock_cdist:
        mock_cdist.return_value = np.array([[1.414, 0.0], [0.0, 1.414]])

        results = spatial_adapter.execute(
            "scipy.spatial.distance.cdist", inputs, params, work_dir=tmp_path
        )

        assert len(results) == 1
        ref = results[0]
        assert ref["format"] == "npy"
        assert ref["path"].endswith(".npy")

        # Verify saved file
        saved_dist = np.load(ref["path"])
        assert saved_dist.shape == (2, 2)
        assert ref["metadata"]["columns_a"] == ["x", "y"]
        assert ref["metadata"]["columns_b"] == ["x", "y"]
        mock_cdist.assert_called_once()


@pytest.mark.requires_base
def test_execute_voronoi(spatial_adapter, tmp_path):
    df = pd.DataFrame({"x": [0.0, 0.0, 1.0, 1.0], "y": [0.0, 1.0, 0.0, 1.0]})
    uri = "obj://test/table"
    object_cache.register(uri, df)

    inputs = [("table", {"uri": uri, "type": "TableRef"})]
    params = {}

    with patch("scipy.spatial.Voronoi") as mock_voronoi:
        mock_obj = MagicMock()
        mock_obj.vertices = np.array([[0.5, 0.5]])
        mock_obj.ridge_points = np.array([[0, 1]])
        mock_obj.ridge_vertices = [[-1, 0]]
        mock_obj.regions = [[], [0]]
        mock_obj.point_region = np.array([0, 1, 0, 1])
        mock_voronoi.return_value = mock_obj

        results = spatial_adapter.execute(
            "scipy.spatial.Voronoi", inputs, params, work_dir=tmp_path
        )

        assert len(results) == 1
        ref = results[0]
        assert ref["format"] == "json"

        with open(ref["path"]) as f:
            data = json.load(f)
            assert "vertices" in data
            assert "ridge_points" in data
            assert data["selected_columns"] == ["x", "y"]
            assert data["vertices"] == [[0.5, 0.5]]


@pytest.mark.requires_base
def test_execute_delaunay(spatial_adapter, tmp_path):
    df = pd.DataFrame({"x": [0.0, 0.0, 1.0, 1.0], "y": [0.0, 1.0, 0.0, 1.0]})
    uri = "obj://test/table_del"
    object_cache.register(uri, df)

    inputs = [("table", {"uri": uri, "type": "TableRef"})]
    params = {}

    with patch("scipy.spatial.Delaunay") as mock_delaunay:
        mock_obj = MagicMock()
        mock_obj.simplices = np.array([[0, 1, 2], [1, 2, 3]])
        mock_obj.neighbors = np.array([[-1, 1, -1], [-1, 0, -1]])
        mock_delaunay.return_value = mock_obj

        results = spatial_adapter.execute(
            "scipy.spatial.Delaunay", inputs, params, work_dir=tmp_path
        )

        assert len(results) == 1
        ref = results[0]
        assert ref["format"] == "json"

        with open(ref["path"]) as f:
            data = json.load(f)
            assert "simplices" in data
            assert "neighbors" in data
            assert data["simplices"] == [[0, 1, 2], [1, 2, 3]]


@pytest.mark.requires_base
def test_cdist_mahalanobis_from_param(spatial_adapter, tmp_path):
    df_a = pd.DataFrame({"x": [0.0, 1.0, 2.0], "y": [0.0, 1.0, 2.0]})
    df_b = pd.DataFrame({"x": [1.0, 0.0, 1.0], "y": [0.0, 1.0, 0.0]})

    uri_a = "obj://test/table_a_mah"
    uri_b = "obj://test/table_b_mah"
    object_cache.register(uri_a, df_a)
    object_cache.register(uri_b, df_b)

    inputs = [
        ("table_a", {"uri": uri_a, "type": "TableRef"}),
        ("table_b", {"uri": uri_b, "type": "TableRef"}),
    ]

    vi = [[1.0, 0.0], [0.0, 1.0]]
    params = {"metric": "mahalanobis", "vi_strategy": "from_param", "vi": vi}

    with patch("scipy.spatial.distance.cdist") as mock_cdist:
        mock_cdist.return_value = np.zeros((3, 3))
        spatial_adapter.execute("scipy.spatial.distance.cdist", inputs, params, work_dir=tmp_path)

        args, kwargs = mock_cdist.call_args
        assert "VI" in kwargs
        np.testing.assert_array_equal(kwargs["VI"], np.array(vi))
