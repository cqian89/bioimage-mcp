from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from mcp.types import ClientCapabilities, ElicitResult, ListRootsResult, Root

from bioimage_mcp.api.permissions import PermissionService
from bioimage_mcp.config.schema import Config, OverwritePolicy, PermissionMode, PermissionSettings


@dataclass
class FakeSession:
    session_id: str
    roots: list[str]
    elicit_result: ElicitResult | dict | None = None
    allow_elicitation: bool = True

    def check_client_capability(self, capability: ClientCapabilities) -> bool:
        if capability.roots is not None:
            return True
        if capability.elicitation is not None:
            return self.allow_elicitation
        return False

    def list_roots(self) -> ListRootsResult:
        return ListRootsResult(roots=[Root(uri=uri) for uri in self.roots])

    def elicit_form(self, message: str, requestedSchema: dict[str, object]) -> ElicitResult | dict:
        if self.elicit_result is None:
            return ElicitResult(action="decline")
        return self.elicit_result


def test_permission_audit_logs_include_inherited_roots(tmp_path: Path, caplog) -> None:
    root = tmp_path / "project"
    root.mkdir()
    session = FakeSession(session_id="session-logs", roots=[root.as_uri()])

    service = PermissionService()

    with caplog.at_level(logging.INFO, logger="bioimage_mcp.api.permissions"):
        service.list_roots(session)

    root_text = str(root.expanduser().absolute())
    assert any(
        "Inherited roots" in record.getMessage() and root_text in record.getMessage()
        for record in caplog.records
    )


def test_permission_audit_logs_include_decisions(tmp_path: Path, caplog) -> None:
    root = tmp_path / "project"
    root.mkdir()
    allowed_target = root / "file.txt"
    denied_target = tmp_path / "elsewhere" / "file.txt"
    denied_target.parent.mkdir(parents=True)

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[],
        fs_allowlist_write=[],
        fs_denylist=[],
        permissions=PermissionSettings(mode=PermissionMode.INHERIT),
    )
    session = FakeSession(session_id="session-logs", roots=[root.as_uri()])

    service = PermissionService()

    with caplog.at_level(logging.INFO, logger="bioimage_mcp.api.permissions"):
        caplog.clear()
        service.check_permission("read", allowed_target, session=session, config=config)
        allowed_text = caplog.text
        caplog.clear()
        service.check_permission("read", denied_target, session=session, config=config)
        denied_text = caplog.text

    assert "Permission ALLOWED" in allowed_text
    assert str(allowed_target.expanduser().absolute()) in allowed_text
    assert "Permission DENIED" in denied_text
    assert str(denied_target.expanduser().absolute()) in denied_text


def test_inherit_allows_read_and_write_under_root(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    target = root / "file.txt"

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[],
        fs_allowlist_write=[],
        fs_denylist=[],
        permissions=PermissionSettings(mode=PermissionMode.INHERIT),
    )
    session = FakeSession(session_id="session-1", roots=[root.as_uri()])

    service = PermissionService()

    read_decision = service.check_permission("read", target, session=session, config=config)
    write_decision = service.check_permission("write", target, session=session, config=config)

    assert read_decision.decision == "ALLOWED"
    assert write_decision.decision == "ALLOWED"


def test_inherit_denies_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    target = tmp_path / "other" / "file.txt"
    target.parent.mkdir(parents=True)

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[],
        fs_allowlist_write=[],
        fs_denylist=[],
        permissions=PermissionSettings(mode=PermissionMode.INHERIT),
    )
    session = FakeSession(session_id="session-1", roots=[root.as_uri()])

    service = PermissionService()
    decision = service.check_permission("read", target, session=session, config=config)

    assert decision.decision == "DENIED"


def test_hybrid_respects_explicit_allowlist(tmp_path: Path) -> None:
    explicit_root = tmp_path / "explicit"
    explicit_root.mkdir()
    target = explicit_root / "file.txt"

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[explicit_root],
        fs_allowlist_write=[explicit_root],
        fs_denylist=[],
        permissions=PermissionSettings(mode=PermissionMode.HYBRID),
    )
    session = FakeSession(session_id="session-2", roots=[])

    service = PermissionService()
    decision = service.check_permission("read", target, session=session, config=config)

    assert decision.decision == "ALLOWED"


def test_elicit_confirmation_allows_overwrite_when_accepted(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    target.write_text("data")

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[],
        fs_allowlist_write=[],
        fs_denylist=[],
        permissions=PermissionSettings(
            mode=PermissionMode.EXPLICIT,
            on_overwrite=OverwritePolicy.ASK,
        ),
    )
    session = FakeSession(
        session_id="session-3",
        roots=[],
        elicit_result=ElicitResult(action="accept", content={"overwrite": True}),
    )

    service = PermissionService()
    decision = service.elicit_confirmation(target, session=session, config=config)

    assert decision == "ALLOWED"


def test_elicit_confirmation_denies_without_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    target.write_text("data")

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[],
        fs_allowlist_write=[],
        fs_denylist=[],
        permissions=PermissionSettings(
            mode=PermissionMode.EXPLICIT,
            on_overwrite=OverwritePolicy.ASK,
        ),
    )
    session = FakeSession(
        session_id="session-4",
        roots=[],
        elicit_result=ElicitResult(action="accept", content={"overwrite": False}),
    )

    service = PermissionService()
    decision = service.elicit_confirmation(target, session=session, config=config)

    assert decision == "DENIED"
