from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from bioimage_mcp.registry.dynamic.adapters.scipy_ndimage import ScipyNdimageAdapter
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern, ParameterSchema

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ScipySignalAdapter(ScipyNdimageAdapter):
    """Adapter for scipy.signal functions."""

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover functions from configured modules."""
        modules = module_config.get("modules", [])
        if "scipy.signal" not in modules:
            return []

        results: list[FunctionMetadata] = []

        # 1) scipy.signal.fftconvolve
        results.append(
            FunctionMetadata(
                name="fftconvolve",
                module="scipy.signal",
                qualified_name="scipy.signal.fftconvolve",
                fn_id="scipy.signal.fftconvolve",
                source_adapter="scipy_signal",
                description="Convolve two N-dimensional arrays using FFT.",
                io_pattern=IOPattern.BINARY,
                tags=["signal", "convolution"],
                parameters={
                    "mode": ParameterSchema(
                        name="mode",
                        type="string",
                        default="same",
                        enum=["full", "same", "valid"],
                        description="A string indicating the size of the output.",
                    )
                },
            )
        )

        # 2) scipy.signal.correlate
        results.append(
            FunctionMetadata(
                name="correlate",
                module="scipy.signal",
                qualified_name="scipy.signal.correlate",
                fn_id="scipy.signal.correlate",
                source_adapter="scipy_signal",
                description="Cross-correlate two N-dimensional arrays.",
                io_pattern=IOPattern.BINARY,
                tags=["signal", "convolution"],
                parameters={
                    "mode": ParameterSchema(
                        name="mode",
                        type="string",
                        default="same",
                        enum=["full", "same", "valid"],
                        description="A string indicating the size of the output.",
                    )
                },
            )
        )

        # 3) scipy.signal.periodogram
        results.append(
            FunctionMetadata(
                name="periodogram",
                module="scipy.signal",
                qualified_name="scipy.signal.periodogram",
                fn_id="scipy.signal.periodogram",
                source_adapter="scipy_signal",
                description="Estimate power spectral density using a periodogram.",
                io_pattern=IOPattern.ANY_TO_TABLE,
                tags=["signal", "spectrum"],
                parameters={
                    "column": ParameterSchema(
                        name="column",
                        type="string",
                        required=False,
                        description="Column name to use if input is a table.",
                    ),
                    "fs": ParameterSchema(
                        name="fs",
                        type="number",
                        default=1.0,
                        description="Sampling frequency of the x time series.",
                    ),
                    "scaling": ParameterSchema(
                        name="scaling",
                        type="string",
                        default="density",
                        enum=["density", "spectrum"],
                        description="Selects between computing the power spectral density or the power spectrum.",
                    ),
                },
            )
        )

        # 4) scipy.signal.welch
        results.append(
            FunctionMetadata(
                name="welch",
                module="scipy.signal",
                qualified_name="scipy.signal.welch",
                fn_id="scipy.signal.welch",
                source_adapter="scipy_signal",
                description="Estimate power spectral density using Welch's method.",
                io_pattern=IOPattern.ANY_TO_TABLE,
                tags=["signal", "spectrum"],
                parameters={
                    "column": ParameterSchema(
                        name="column",
                        type="string",
                        required=False,
                        description="Column name to use if input is a table.",
                    ),
                    "fs": ParameterSchema(
                        name="fs",
                        type="number",
                        default=1.0,
                        description="Sampling frequency of the x time series.",
                    ),
                    "nperseg": ParameterSchema(
                        name="nperseg",
                        type="integer",
                        required=False,
                        description="Length of each segment.",
                    ),
                    "noverlap": ParameterSchema(
                        name="noverlap",
                        type="integer",
                        required=False,
                        description="Number of points to overlap between segments.",
                    ),
                    "scaling": ParameterSchema(
                        name="scaling",
                        type="string",
                        default="density",
                        enum=["density", "spectrum"],
                        description="Selects between computing the power spectral density or the power spectrum.",
                    ),
                },
            )
        )

        return results

    def execute(
        self,
        fn_id: str,
        inputs: list[tuple[str, Any]],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        """Execute signal functions."""
        import numpy as np
        import pandas as pd
        import scipy.signal

        from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry

        input_dict = dict(inputs)

        if fn_id in ["scipy.signal.fftconvolve", "scipy.signal.correlate"]:
            # 1) Load image (port name is 'image' for BINARY)
            image_ref = input_dict.get("image")
            if not image_ref and inputs:
                image_ref = inputs[0][1]

            if not image_ref:
                raise ValueError(f"{fn_id} requires an image artifact as 'image'")

            image = self._load_image(image_ref)
            axes = self._extract_axes(image_ref)

            # Extract pass-through metadata
            metadata_override = {}
            meta = (
                image_ref.get("metadata", {})
                if isinstance(image_ref, dict)
                else getattr(image_ref, "metadata", {})
            )
            if meta:
                if "physical_pixel_sizes" in meta:
                    metadata_override["physical_pixel_sizes"] = meta["physical_pixel_sizes"]
                if "channel_names" in meta:
                    metadata_override["channel_names"] = meta["channel_names"]

            # 2) Load kernel (port name is 'input_1' for BINARY)
            kernel_ref = input_dict.get("input_1")
            if not kernel_ref and len(inputs) > 1:
                # Fallback if names are missing but order is preserved
                if inputs[0][0] == "image":
                    kernel_ref = inputs[1][1]
                else:
                    # Fallback to second input if first was already consumed as image
                    if image_ref is inputs[0][1]:
                        kernel_ref = inputs[1][1]

            if not kernel_ref:
                raise ValueError(f"{fn_id} requires a kernel artifact as 'input_1'")

            kernel = self._load_image(kernel_ref)

            # 3) Kernel shape handling: if kernel.ndim < image.ndim, left-pad kernel
            if kernel.ndim < image.ndim:
                pad_width = image.ndim - kernel.ndim
                kernel = kernel.reshape((1,) * pad_width + kernel.shape)

            mode = params.get("mode", "same")

            if fn_id == "scipy.signal.fftconvolve":
                result = scipy.signal.fftconvolve(image, kernel, mode=mode)
            else:
                result = scipy.signal.correlate(image, kernel, mode=mode, method="fft")

            return [
                self._save_image(
                    result, work_dir=work_dir, axes=axes, metadata_override=metadata_override
                )
            ]

        if fn_id in ["scipy.signal.periodogram", "scipy.signal.welch"]:
            # Load single input (port name is 'input' for ANY_TO_TABLE)
            art_ref = input_dict.get("input")
            if not art_ref and inputs:
                art_ref = inputs[0][1]

            if not art_ref:
                raise ValueError(f"{fn_id} requires an input artifact")

            # Load x (1D signal)
            x = None
            is_bioimage = False
            if isinstance(art_ref, dict):
                is_bioimage = art_ref.get("type") == "BioImageRef"
            elif isinstance(art_ref, str):
                is_bioimage = False
            else:
                is_bioimage = getattr(art_ref, "type", None) == "BioImageRef"

            if is_bioimage:
                arr = self._load_image(art_ref)
                x = np.squeeze(arr)
                if x.ndim != 1:
                    raise ValueError(f"{fn_id} requires a 1D signal; got {x.ndim}D after squeeze")
            else:
                # Assume TableRef or ObjectRef holding DataFrame
                df = PandasAdapterForRegistry()._load_table(art_ref)
                col = params.get("column")
                if col:
                    if col not in df.columns:
                        raise ValueError(f"Column '{col}' not found in table")
                    x = df[col].values
                else:
                    # Auto-select first numeric column
                    numeric_cols = df.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) == 0:
                        raise ValueError("No numeric columns found in table")
                    x = df[numeric_cols[0]].values

            fs = params.get("fs", 1.0)
            scaling = params.get("scaling", "density")

            if fn_id == "scipy.signal.periodogram":
                f, Pxx = scipy.signal.periodogram(x, fs=fs, scaling=scaling)
                res_df = pd.DataFrame({"frequency": f, "power": Pxx})
                return PandasAdapterForRegistry()._save_table(
                    res_df, name="periodogram", work_dir=work_dir
                )
            else:
                nperseg = params.get("nperseg")
                noverlap = params.get("noverlap")
                f, Pxx = scipy.signal.welch(
                    x, fs=fs, nperseg=nperseg, noverlap=noverlap, scaling=scaling
                )
                res_df = pd.DataFrame({"frequency": f, "psd": Pxx})
                return PandasAdapterForRegistry()._save_table(
                    res_df, name="welch", work_dir=work_dir
                )

        return super().execute(fn_id, inputs, params, work_dir)
