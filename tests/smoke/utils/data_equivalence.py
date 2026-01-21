from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from numpy.testing import assert_allclose
from scipy.optimize import linear_sum_assignment
from PIL import Image


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
        expected_width: Optional[int] = None,
        expected_height: Optional[int] = None,
        min_variance: float = 1.0,
    ) -> None:
        """Semantic validation of plot artifact."""
        assert path.exists(), f"Plot file {path} does not exist"

        size = path.stat().st_size
        assert size >= min_size, f"Plot file {path} too small ({size} < {min_size} bytes)"

        with Image.open(path) as img:
            if expected_width is not None:
                assert img.width == expected_width, (
                    f"Expected width {expected_width}, got {img.width}"
                )
            if expected_height is not None:
                assert img.height == expected_height, (
                    f"Expected height {expected_height}, got {img.height}"
                )

            # Check for non-blank content
            data = np.array(img)
            # Use variance to detect "blank" or single-color images
            variance = np.var(data)
            assert variance >= min_variance, (
                f"Plot {path} appears blank (variance {variance:.4f} < {min_variance})"
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
