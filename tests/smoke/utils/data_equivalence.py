from __future__ import annotations

from pathlib import Path

from typing import Any
import numpy as np
import pandas as pd
from numpy.testing import assert_allclose
from PIL import Image
from scipy.optimize import linear_sum_assignment


class DataEquivalenceHelper:
    def assert_arrays_equivalent(
        self,
        actual: np.ndarray,
        expected: np.ndarray,
        rtol: float = 1e-5,
        atol: float = 1e-8,
        err_msg: str = "",
    ) -> None:
        """Compare float arrays with tolerance."""
        actual_sq = np.squeeze(actual)
        expected_sq = np.squeeze(expected)
        assert_allclose(actual_sq, expected_sq, rtol=rtol, atol=atol, err_msg=err_msg)

    def assert_labels_equivalent(
        self, actual: np.ndarray, expected: np.ndarray, iou_threshold: float = 0.99
    ) -> float:
        """Compare label images using IoU matching. Returns mean IoU."""
        actual_sq = np.squeeze(actual)
        expected_sq = np.squeeze(expected)

        labels_actual = np.unique(actual_sq)
        labels_actual = labels_actual[labels_actual != 0]
        labels_expected = np.unique(expected_sq)
        labels_expected = labels_expected[labels_expected != 0]

        if len(labels_actual) == 0 and len(labels_expected) == 0:
            return 1.0
        if len(labels_actual) == 0 or len(labels_expected) == 0:
            assert 0.0 >= iou_threshold, f"One label image is empty. IoU=0.0 < {iou_threshold}"
            return 0.0

        # Compute IoU matrix
        iou_matrix = np.zeros((len(labels_actual), len(labels_expected)))
        for i, la in enumerate(labels_actual):
            mask_a = actual_sq == la
            for j, le in enumerate(labels_expected):
                mask_e = expected_sq == le
                intersection = np.logical_and(mask_a, mask_e).sum()
                union = np.logical_or(mask_a, mask_e).sum()
                iou_matrix[i, j] = intersection / union if union > 0 else 0

        # Hungarian matching
        row_ind, col_ind = linear_sum_assignment(1 - iou_matrix)
        matched_ious = iou_matrix[row_ind, col_ind]

        # Mean IoU over all labels (penalize missing/extra labels)
        mean_iou = matched_ious.sum() / max(len(labels_actual), len(labels_expected))

        assert mean_iou >= iou_threshold, f"Mean IoU {mean_iou:.4f} < {iou_threshold}"
        return float(mean_iou)

    def assert_plot_valid(
        self,
        path: Path,
        min_size: int = 1000,
        expected_width: int | None = None,
        expected_height: int | None = None,
        dimension_tolerance: int = 0,
        min_variance: float = 1.0,
        min_mean: float | None = None,
        max_mean: float | None = None,
        min_std: float | None = None,
        max_std: float | None = None,
    ) -> None:
        """Semantic validation of plot artifact."""
        assert path.exists(), f"Plot file {path} does not exist"

        size = path.stat().st_size
        assert size >= min_size, f"Plot file {path} too small ({size} < {min_size} bytes)"

        with Image.open(path) as img:
            if expected_width is not None:
                assert abs(img.width - expected_width) <= dimension_tolerance, (
                    f"Expected width {expected_width} (±{dimension_tolerance}), got {img.width}"
                )
            if expected_height is not None:
                assert abs(img.height - expected_height) <= dimension_tolerance, (
                    f"Expected height {expected_height} (±{dimension_tolerance}), got {img.height}"
                )

            # Check for non-blank content
            data = np.array(img)
            # Use variance to detect "blank" or single-color images
            variance = np.var(data)
            assert variance >= min_variance, (
                f"Plot {path} appears blank (variance {variance:.4f} < {min_variance})"
            )

            # Optional intensity statistics validation
            if (
                min_mean is not None
                or max_mean is not None
                or min_std is not None
                or max_std is not None
            ):
                mean = np.mean(data)
                std = np.std(data)
                if min_mean is not None:
                    assert mean >= min_mean, f"Plot {path} mean {mean:.4f} < {min_mean}"
                if max_mean is not None:
                    assert mean <= max_mean, f"Plot {path} mean {mean:.4f} > {max_mean}"
                if min_std is not None:
                    assert std >= min_std, f"Plot {path} std {std:.4f} < {min_std}"
                if max_std is not None:
                    assert std <= max_std, f"Plot {path} std {std:.4f} > {max_std}"

    def assert_files_similar_size(self, path1: Path, path2: Path, max_ratio: float = 2.0) -> None:
        """Check that two files have similar sizes (within a ratio)."""
        size1 = path1.stat().st_size
        size2 = path2.stat().st_size

        if size1 == 0 or size2 == 0:
            assert size1 == size2, f"One file is empty: {size1} vs {size2} bytes"
            return

        ratio = max(size1, size2) / min(size1, size2)

        assert ratio <= max_ratio, (
            f"File sizes differ too much: {path1.name} ({size1} bytes) vs "
            f"{path2.name} ({size2} bytes). Ratio {ratio:.2f} > {max_ratio}"
        )

    def assert_table_equivalent(
        self,
        actual: pd.DataFrame,
        expected: pd.DataFrame,
        rtol: float = 1e-5,
        check_column_order: bool = False,
    ) -> None:
        """Compare table artifacts."""
        if not check_column_order:
            actual = actual.reindex(columns=sorted(actual.columns))
            expected = expected.reindex(columns=sorted(expected.columns))

        pd.testing.assert_frame_equal(actual, expected, rtol=rtol)

    def assert_metadata_preserved(self, actual: Any, expected: Any) -> None:
        """
        Assert metadata (dims, coords, attrs for xarray; columns, index for pandas) is preserved.

        Args:
            actual: Actual data object (DataArray or DataFrame)
            expected: Expected data object
        """
        import xarray as xr

        # Xarray DataArray
        if isinstance(actual, xr.DataArray) and isinstance(expected, xr.DataArray):
            # Check dimensions
            assert actual.dims == expected.dims, (
                f"xarray dimension names differ: {actual.dims} != {expected.dims}"
            )

            # Check coordinates
            if not actual.coords.equals(expected.coords):
                raise AssertionError(
                    f"xarray coordinates differ:\nActual: {actual.coords}\nExpected: {expected.coords}"
                )

            # Check attributes
            if actual.attrs != expected.attrs:
                raise AssertionError(
                    f"xarray attributes differ:\nActual: {actual.attrs}\nExpected: {expected.attrs}"
                )

        # Pandas DataFrame
        elif isinstance(actual, pd.DataFrame) and isinstance(expected, pd.DataFrame):
            # Check columns
            assert list(actual.columns) == list(expected.columns), (
                f"DataFrame columns differ: {list(actual.columns)} != {list(expected.columns)}"
            )

            # Check index names
            assert actual.index.names == expected.index.names, (
                f"DataFrame index names differ: {actual.index.names} != {expected.index.names}"
            )
        else:
            # Fallback for other types if needed, or just skip if types don't support metadata
            pass
