from __future__ import annotations

import pytest

from bioimage_mcp.registry.dynamic.adapters.scipy_signal import ScipySignalAdapter
from bioimage_mcp.registry.dynamic.models import IOPattern


@pytest.mark.requires_base
def test_scipy_signal_adapter_discovery():
    adapter = ScipySignalAdapter()
    config = {"modules": ["scipy.signal"]}
    discovery = adapter.discover(config)

    fn_ids = [m.fn_id for m in discovery]
    assert "scipy.signal.fftconvolve" in fn_ids
    assert "scipy.signal.correlate" in fn_ids
    assert "scipy.signal.periodogram" in fn_ids
    assert "scipy.signal.welch" in fn_ids

    # Check IO patterns
    for m in discovery:
        if m.fn_id == "scipy.signal.fftconvolve":
            assert m.io_pattern == IOPattern.BINARY
        if m.fn_id == "scipy.signal.periodogram":
            assert m.io_pattern == IOPattern.ANY_TO_TABLE


@pytest.mark.requires_base
def test_scipy_signal_composite_discovery():
    from bioimage_mcp.registry.dynamic.adapters.scipy import ScipyAdapter

    adapter = ScipyAdapter()
    config = {"modules": ["scipy.signal"]}
    discovery = adapter.discover(config)

    fn_ids = [m.fn_id for m in discovery]
    assert "scipy.signal.periodogram" in fn_ids
