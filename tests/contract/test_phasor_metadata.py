import pytest
from pydantic import ValidationError

from bioimage_mcp.artifacts.models import PhasorMetadata


def test_phasor_metadata_validation():
    # Valid metadata
    meta = PhasorMetadata(component="real", harmonic=1, is_calibrated=True)
    assert meta.component == "real"
    assert meta.harmonic == 1
    assert meta.is_calibrated is True

    # Invalid component
    with pytest.raises(ValidationError):
        PhasorMetadata(component="invalid")

    # Optional fields
    meta = PhasorMetadata(component="imag", frequency_hz=80.0e6, reference_lifetime_ns=4.0)
    assert meta.frequency_hz == 80.0e6
    assert meta.reference_lifetime_ns == 4.0
