from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioimage_mcp.config.schema import Config

logger = logging.getLogger(__name__)


class StorageService:
    """Service for artifact storage management, retention, and quota enforcement."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.storage_config = config.storage
        self.root = config.artifact_store_root
        logger.debug("StorageService initialized with root: %s", self.root)
