from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from bioimage_mcp.config.schema import Config
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.sessions.models import Session
from bioimage_mcp.sessions.store import SessionStore


class SessionManager:
    """Manages session lifecycle and activity tracking."""

    def __init__(self, store: SessionStore, config: Config) -> None:
        self.store = store
        self.config = config

    def check_expiry(self, session_id: str) -> None:
        """Check if session is expired and update status if so."""
        try:
            session = self.store.get_session(session_id)
            self._validate_session_expiry(session)
        except KeyError:
            # Session doesn't exist, nothing to expire
            pass

    def _validate_session_expiry(self, session: Session) -> None:
        """Helper to check expiry on a Session object."""
        if session.status == "expired":
            raise ValueError(f"Session {session.session_id} is expired")

        last_activity = datetime.fromisoformat(session.last_activity_at)
        age = datetime.now(UTC) - last_activity

        if age.total_seconds() > (self.config.session_ttl_hours * 3600):
            self.store.update_session_status(session.session_id, "expired")
            raise ValueError(f"Session {session.session_id} is expired")

    def ensure_session(self, session_id: str, connection_hint: str | None = None) -> Session:
        """
        Get an existing session or create a new one.
        Updates activity timestamp for existing sessions.
        """
        try:
            session = self.store.get_session(session_id)
            self._validate_session_expiry(session)
            # If found and valid, update activity and return updated session
            return self.store.update_activity(session_id)
        except KeyError:
            # If not found, create new
            return self.store.create_session(session_id, connection_hint=connection_hint)

    def update_activity(self, session_id: str) -> None:
        """Update the last activity timestamp for a session."""
        self.store.update_activity(session_id)

    def get_session(self, session_id: str) -> Session:
        """Get a session by ID."""
        session = self.store.get_session(session_id)
        self._validate_session_expiry(session)
        return session

    def get_function_provenance(self, fn_id: str) -> dict[str, str]:
        """Get provenance metadata for a function (T113)."""
        manifests, _ = load_manifests(self.config.tool_manifest_roots)
        for manifest in manifests:
            for fn in manifest.functions:
                if fn.fn_id == fn_id:
                    try:
                        manifest_content = Path(manifest.manifest_path).read_bytes()
                        lock_hash = hashlib.sha256(manifest_content).hexdigest()
                    except (OSError, TypeError):
                        lock_hash = "unavailable"

                    return {
                        "tool_pack_id": manifest.tool_id,
                        "tool_pack_version": manifest.tool_version,
                        "lock_hash": lock_hash,
                    }
        return {
            "tool_pack_id": "unknown",
            "tool_pack_version": "0.0.0",
            "lock_hash": "unavailable",
        }
