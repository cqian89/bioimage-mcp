from __future__ import annotations

import logging

from bioimage_mcp.logging import configure_logging, get_logger


def test_get_logger_returns_configured_logger() -> None:
    # Reset handlers for test isolation
    root = logging.getLogger("bioimage_mcp")
    root.handlers.clear()

    logger = get_logger("test.module")
    assert logger.name == "test.module"


def test_configure_logging_is_idempotent() -> None:
    # Reset handlers for test isolation
    root = logging.getLogger("bioimage_mcp")
    root.handlers.clear()

    configure_logging("DEBUG")
    configure_logging("DEBUG")  # Should not add duplicate handlers
    root = logging.getLogger("bioimage_mcp")
    assert len(root.handlers) == 1


def test_configure_logging_respects_level() -> None:
    # Reset handlers for test isolation
    root = logging.getLogger("bioimage_mcp")
    root.handlers.clear()

    configure_logging("WARNING")
    root = logging.getLogger("bioimage_mcp")
    assert root.level == logging.WARNING


def test_get_logger_default_name() -> None:
    # Reset handlers for test isolation
    root = logging.getLogger("bioimage_mcp")
    root.handlers.clear()

    logger = get_logger()
    assert logger.name == "bioimage_mcp"
