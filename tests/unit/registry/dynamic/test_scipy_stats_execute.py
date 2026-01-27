from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from bioimage_mcp.registry.dynamic import object_cache
from bioimage_mcp.registry.dynamic.adapters.scipy_stats import ScipyStatsAdapter


@pytest.fixture
def stats_adapter():
    return ScipyStatsAdapter()


@pytest.mark.requires_base
def test_ttest_ind_table_execution(stats_adapter, tmp_path):
    """ttest_ind_table should execute on two tables and return JSON with stats."""
    # Setup cache with two dataframes
    df_a = pd.DataFrame({"val": [1, 2, 3]})
    df_b = pd.DataFrame({"val": [4, 5, 6]})

    uri_a = "obj://session/env/table_a"
    uri_b = "obj://session/env/table_b"
    object_cache.register(uri_a, df_a)
    object_cache.register(uri_b, df_b)

    # Mock scipy.stats.ttest_ind
    with patch("scipy.stats.ttest_ind") as mock_ttest:
        # SciPy tests often return a namedtuple-like object
        mock_result = MagicMock()
        mock_result.statistic = -3.0
        mock_result.pvalue = 0.05
        mock_result._asdict.return_value = {"statistic": -3.0, "pvalue": 0.05}
        mock_ttest.return_value = mock_result

        inputs = [
            ("table_a", {"uri": uri_a, "type": "TableRef"}),
            ("table_b", {"uri": uri_b, "type": "TableRef"}),
        ]

        outputs = stats_adapter.execute(
            fn_id="scipy.stats.ttest_ind_table",
            inputs=inputs,
            params={"column": "val"},
            work_dir=tmp_path,
        )

        assert len(outputs) == 1
        assert outputs[0]["type"] == "NativeOutputRef"
        assert outputs[0]["format"] == "json"

        # Verify call
        mock_ttest.assert_called_once()
        # First arg should be the values from df_a
        np.testing.assert_array_equal(mock_ttest.call_args[0][0], df_a["val"].values)
        np.testing.assert_array_equal(mock_ttest.call_args[0][1], df_b["val"].values)


@pytest.mark.requires_base
def test_describe_table_auto_column_selection(stats_adapter, tmp_path):
    """describe_table should auto-select first numeric column if none provided."""
    # DF with one non-numeric and two numeric columns
    df = pd.DataFrame(
        {"label": ["A", "B", "C"], "area": [10, 20, 30], "intensity": [100, 200, 300]}
    )

    uri = "obj://session/env/multi_col"
    object_cache.register(uri, df)

    with patch("scipy.stats.describe") as mock_describe:
        mock_result = MagicMock()
        mock_result.nobs = 3
        # ... other fields
        mock_result._asdict.return_value = {"nobs": 3, "mean": 20.0}
        mock_describe.return_value = mock_result

        outputs = stats_adapter.execute(
            fn_id="scipy.stats.describe_table",
            inputs=[("table", {"uri": uri, "type": "TableRef"})],
            params={},
            work_dir=tmp_path,
        )

        # describe should have been called with the first numeric column "area"
        np.testing.assert_array_equal(mock_describe.call_args[0][0], df["area"].values)

        # Verify payload contains selected_columns
        import json

        with open(outputs[0]["uri"].replace("file://", "")) as f:
            payload = json.load(f)
            assert payload["selected_columns"] == ["area"]


@pytest.mark.requires_base
def test_distribution_cdf_execution(stats_adapter, tmp_path):
    """Distribution methods like norm.cdf should execute correctly."""
    with patch("scipy.stats.norm") as mock_norm:
        mock_frozen = MagicMock()
        mock_frozen.cdf.return_value = np.array([0.5])
        mock_norm.return_value = mock_frozen

        outputs = stats_adapter.execute(
            fn_id="scipy.stats.norm.cdf",
            inputs=[],
            params={"x": [0], "loc": 0, "scale": 1},
            work_dir=tmp_path,
        )

        assert len(outputs) == 1
        # norm() should be called with loc/scale
        mock_norm.assert_called_once_with(loc=0, scale=1)
        # cdf() should be called with [0]
        mock_frozen.cdf.assert_called_once_with([0])

        # Check output value
        import json

        with open(outputs[0]["uri"].replace("file://", "")) as f:
            val = json.load(f)
            assert val == [0.5]
