from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from bioimage_mcp.registry.dynamic.adapters.scipy_signal import ScipySignalAdapter


@pytest.fixture
def adapter():
    return ScipySignalAdapter()


@pytest.mark.requires_base
def test_scipy_signal_fftconvolve_execution(adapter):
    img = np.zeros((10, 10))
    img[5, 5] = 1.0
    kernel = np.ones((3, 3))

    img_ref = {"type": "BioImageRef", "uri": "file:///tmp/img.ome.tiff", "metadata": {"axes": "YX"}}
    kernel_ref = {"type": "BioImageRef", "uri": "file:///tmp/kernel.ome.tiff"}

    inputs = [("image", img_ref), ("input_1", kernel_ref)]
    params = {"mode": "same"}

    with patch.object(adapter, "_load_image") as mock_load:
        mock_load.side_effect = [img, kernel]
        with patch.object(adapter, "_save_image") as mock_save:
            mock_save.return_value = {"type": "BioImageRef", "uri": "output"}

            result = adapter.execute("scipy.signal.fftconvolve", inputs, params)

            assert len(result) == 1
            assert result[0]["type"] == "BioImageRef"
            mock_save.assert_called_once()
            args, kwargs = mock_save.call_args
            assert args[0].shape == (10, 10)
            assert kwargs["axes"] == "YX"


@pytest.mark.requires_base
def test_scipy_signal_periodogram_table_execution(adapter):
    df = pd.DataFrame({"signal": np.sin(np.linspace(0, 10, 100))})
    art_ref = {"type": "TableRef", "uri": "file:///tmp/table.parquet"}

    inputs = [("input", art_ref)]
    params = {"column": "signal", "fs": 10.0}

    from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry

    with patch.object(PandasAdapterForRegistry, "_load_table", return_value=df):
        with patch.object(PandasAdapterForRegistry, "_save_table") as mock_save:
            mock_save.return_value = [{"type": "TableRef"}]

            result = adapter.execute("scipy.signal.periodogram", inputs, params)

            assert len(result) == 1
            mock_save.assert_called_once()
            saved_df = mock_save.call_args[0][0]
            assert "frequency" in saved_df.columns
            assert "power" in saved_df.columns


@pytest.mark.requires_base
def test_scipy_signal_welch_bioimage_execution(adapter):
    # 1D signal wrapped in 5D BioImage shape (T, C, Z, Y, X) -> (1, 1, 1, 1, 100)
    img = np.zeros((1, 1, 1, 1, 100))
    img[0, 0, 0, 0, :] = np.sin(np.linspace(0, 10, 100))

    art_ref = {"type": "BioImageRef", "uri": "file:///tmp/img.ome.tiff"}

    inputs = [("input", art_ref)]
    params = {"fs": 1.0}

    with patch.object(adapter, "_load_image", return_value=img):
        from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry

        with patch.object(PandasAdapterForRegistry, "_save_table") as mock_save:
            mock_save.return_value = [{"type": "TableRef"}]

            result = adapter.execute("scipy.signal.welch", inputs, params)

            assert len(result) == 1
            mock_save.assert_called_once()
            saved_df = mock_save.call_args[0][0]
            assert "frequency" in saved_df.columns
            assert "psd" in saved_df.columns


@pytest.mark.requires_base
def test_scipy_signal_periodogram_string_input(adapter):
    df = pd.DataFrame({"signal": np.sin(np.linspace(0, 10, 100))})
    # Plain string URI as input
    art_ref = "file:///tmp/table.parquet"

    inputs = [("input", art_ref)]
    params = {"column": "signal", "fs": 10.0}

    from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry

    with patch.object(PandasAdapterForRegistry, "_load_table", return_value=df):
        with patch.object(PandasAdapterForRegistry, "_save_table") as mock_save:
            mock_save.return_value = [{"type": "TableRef"}]

            result = adapter.execute("scipy.signal.periodogram", inputs, params)

            assert len(result) == 1
            mock_save.assert_called_once()
            saved_df = mock_save.call_args[0][0]
            assert "frequency" in saved_df.columns
            assert "power" in saved_df.columns
