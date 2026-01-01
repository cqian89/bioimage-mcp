from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from mcp.types import ClientCapabilities, ElicitationCapability, RootsCapability

from bioimage_mcp.api.schemas import PermissionDecision
from bioimage_mcp.api.schemas import PermissionMode as ApiPermissionMode
from bioimage_mcp.config.schema import Config, OverwritePolicy, PermissionMode

logger = logging.getLogger(__name__)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _session_identifier(session: Any) -> str:
    if hasattr(session, "session_id"):
        value = session.session_id
        if value:
            return str(value)
    if hasattr(session, "id"):
        value = session.id
        if value:
            return str(value)
    return f"session_{id(session)}"


class PermissionService:
    """Permission checks and audit logging for file system access."""

    def __init__(self, *, cache_ttl_seconds: float = 5.0) -> None:
        self._cache_ttl_seconds = cache_ttl_seconds
        self._roots_cache: dict[str, tuple[float, list[Path]]] = {}

    def list_roots(self, session: Any) -> list[Path]:
        if session is None:
            return []

        session_id = _session_identifier(session)
        cached = self._roots_cache.get(session_id)
        now = time.monotonic()
        if cached and now - cached[0] < self._cache_ttl_seconds:
            return cached[1]

        try:
            if hasattr(session, "check_client_capability"):
                capability = ClientCapabilities(roots=RootsCapability())
                if not session.check_client_capability(capability):
                    return []
        except Exception:  # noqa: BLE001
            logger.info("Failed roots capability check for %s", session_id, exc_info=True)
            return []

        try:
            roots_result = session.list_roots()
        except Exception:  # noqa: BLE001
            logger.info("Failed to list roots for %s", session_id, exc_info=True)
            return []

        roots: list[Any] = []
        if roots_result is None:
            roots = []
        elif hasattr(roots_result, "roots"):
            roots = roots_result.roots or []
        elif isinstance(roots_result, dict):
            roots = roots_result.get("roots") or []
        elif isinstance(roots_result, (list, tuple)):
            roots = list(roots_result)

        parsed_roots: list[Path] = []
        for root in roots:
            uri = None
            root_path: Path | None = None
            if isinstance(root, Path):
                root_path = root
            elif isinstance(root, str):
                uri = root
            elif isinstance(root, dict):
                uri = root.get("uri")
            elif hasattr(root, "uri"):
                uri = root.uri

            if root_path is not None:
                parsed_roots.append(root_path.expanduser().absolute())
                continue

            if not uri:
                continue
            if not isinstance(uri, str):
                uri = str(uri)

            parsed = urlparse(uri)
            if parsed.scheme and parsed.scheme != "file":
                continue

            if parsed.scheme == "file":
                root_path = Path(unquote(parsed.path))
                if parsed.netloc:
                    root_path = Path(unquote(f"/{parsed.netloc}{parsed.path}"))
            else:
                root_path = Path(uri)

            parsed_roots.append(root_path.expanduser().absolute())

        self._roots_cache[session_id] = (now, parsed_roots)
        logger.info("Session %s started. Inherited roots: %s", session_id, parsed_roots)
        return parsed_roots

    def check_permission(
        self,
        operation: str,
        path: str | Path,
        *,
        session: Any,
        config: Config,
    ) -> PermissionDecision:
        target = path if isinstance(path, Path) else Path(path)
        target = target.expanduser().absolute()
        decision_mode = ApiPermissionMode(config.permissions.mode.value)

        for deny_root in config.fs_denylist:
            if _is_within(target, deny_root):
                reason = f"Path denied by fs_denylist: {deny_root}"
                decision = PermissionDecision(
                    operation=operation,
                    path=str(target),
                    mode=decision_mode,
                    decision="DENIED",
                    reason=reason,
                    timestamp=datetime.now(tz=UTC),
                )
                logger.info(
                    "Permission %s for %s: %s (Reason: %s)",
                    decision.decision,
                    operation.upper(),
                    target,
                    reason,
                )
                return decision

        allow_roots: list[Path] = []
        explicit_roots = (
            config.fs_allowlist_read if operation == "read" else config.fs_allowlist_write
        )

        if config.permissions.mode == PermissionMode.EXPLICIT:
            allow_roots = explicit_roots
        elif config.permissions.mode == PermissionMode.INHERIT:
            allow_roots = self.list_roots(session)
        elif config.permissions.mode == PermissionMode.HYBRID:
            allow_roots = [*explicit_roots, *self.list_roots(session)]

        if not allow_roots:
            reason = f"No allowed {operation} roots configured"
            decision = PermissionDecision(
                operation=operation,
                path=str(target),
                mode=decision_mode,
                decision="DENIED",
                reason=reason,
                timestamp=datetime.now(tz=UTC),
            )
            logger.info(
                "Permission %s for %s: %s (Reason: %s)",
                decision.decision,
                operation.upper(),
                target,
                reason,
            )
            return decision

        for allow_root in allow_roots:
            if _is_within(target, allow_root):
                root_reason = (
                    "Under inherited root"
                    if config.permissions.mode == PermissionMode.INHERIT
                    else "Under allowed root"
                )
                reason = f"{root_reason}: {allow_root}"
                decision = PermissionDecision(
                    operation=operation,
                    path=str(target),
                    mode=decision_mode,
                    decision="ALLOWED",
                    reason=reason,
                    timestamp=datetime.now(tz=UTC),
                )
                logger.info(
                    "Permission %s for %s: %s (Reason: %s)",
                    decision.decision,
                    operation.upper(),
                    target,
                    reason,
                )
                return decision

        reason = f"Path not under any allowed {operation} root"
        decision = PermissionDecision(
            operation=operation,
            path=str(target),
            mode=decision_mode,
            decision="DENIED",
            reason=reason,
            timestamp=datetime.now(tz=UTC),
        )
        logger.info(
            "Permission %s for %s: %s (Reason: %s)",
            decision.decision,
            operation.upper(),
            target,
            reason,
        )
        return decision

    def elicit_confirmation(self, path: str | Path, *, session: Any, config: Config) -> str:
        policy = config.permissions.on_overwrite
        target = path if isinstance(path, Path) else Path(path)
        target = target.expanduser().absolute()

        if policy == OverwritePolicy.ALLOW:
            return "ALLOWED"
        if policy == OverwritePolicy.DENY:
            return "DENIED"
        if not target.exists():
            return "ALLOWED"
        if session is None:
            return "DENIED"

        try:
            if hasattr(session, "check_client_capability"):
                capability = ClientCapabilities(elicitation=ElicitationCapability())
                if not session.check_client_capability(capability):
                    return "DENIED"
        except Exception:  # noqa: BLE001
            logger.info("Failed elicitation capability check", exc_info=True)
            return "DENIED"

        message = f"The file already exists: {target}. Overwrite it?"
        requested_schema = {
            "type": "object",
            "properties": {
                "overwrite": {
                    "type": "boolean",
                    "title": "Overwrite existing file?",
                }
            },
            "required": ["overwrite"],
            "additionalProperties": False,
        }

        try:
            response = session.elicit_form(message, requestedSchema=requested_schema)
        except TypeError:
            response = session.elicit_form(message, requested_schema)
        except Exception:  # noqa: BLE001
            logger.info("Failed to elicit confirmation", exc_info=True)
            return "DENIED"

        if asyncio.iscoroutine(response):
            try:
                response = asyncio.run(response)
            except RuntimeError:
                logger.info("Cannot await elicitation response in running loop")
                return "DENIED"

        action = None
        content = None
        if isinstance(response, dict):
            action = response.get("action")
            content = response.get("content")
            if content is None and "overwrite" in response:
                content = {"overwrite": response.get("overwrite")}
        elif hasattr(response, "action"):
            action = response.action
            content = getattr(response, "content", None)

        overwrite_allowed = False
        if isinstance(content, dict):
            overwrite_allowed = content.get("overwrite") is True

        if action == "accept" and overwrite_allowed:
            return "ALLOWED"
        if action in {"decline", "cancel"}:
            return "DENIED"

        return "DENIED"
