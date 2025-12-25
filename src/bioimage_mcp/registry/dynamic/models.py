"""
Data models for dynamic function registry.

Defines the core models for introspecting and representing dynamically
discovered functions from Python libraries.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IOPattern(str, Enum):
    """Categorization of function I/O behavior."""

    IMAGE_TO_IMAGE = "image_to_image"
    IMAGE_TO_LABELS = "image_to_labels"
    LABELS_TO_TABLE = "labels_to_table"
    SIGNAL_TO_PHASOR = "signal_to_phasor"
    PHASOR_TRANSFORM = "phasor_transform"
    PHASOR_TO_OTHER = "phasor_to_other"
    ARRAY_TO_ARRAY = "array_to_array"
    ARRAY_TO_SCALAR = "array_to_scalar"
    FILE_TO_SIGNAL = "file_to_signal"
    GENERIC = "generic"


class ParameterSchema(BaseModel):
    """JSON Schema definition for a function parameter."""

    name: str
    type: str
    description: str = ""
    default: Optional[Any] = None
    required: bool = True
    enum: Optional[List[Any]] = None


class FunctionMetadata(BaseModel):
    """Result of introspecting a single function."""

    name: str
    module: str
    qualified_name: str
    fn_id: str
    source_adapter: str
    description: str = ""
    parameters: Dict[str, ParameterSchema] = Field(default_factory=dict)
    io_pattern: IOPattern = IOPattern.GENERIC
    tags: List[str] = Field(default_factory=list)
