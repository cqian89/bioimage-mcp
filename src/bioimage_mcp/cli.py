from __future__ import annotations

import argparse
import json
import sys

from bioimage_mcp.errors import BioimageMcpError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bioimage-mcp")
    parser.add_argument("--debug", action="store_true", help="Show tracebacks on errors")

    subparsers = parser.add_subparsers(dest="command", required=True)

    install = subparsers.add_parser("install", help="Install base environments")
    install.add_argument("--profile", choices=["cpu", "gpu"], default="cpu")
    install.set_defaults(_handler=_handle_install)

    doctor = subparsers.add_parser("doctor", help="Check local readiness")
    doctor.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    doctor.set_defaults(_handler=_handle_doctor)

    configure = subparsers.add_parser("configure", help="Write starter configuration")
    configure.set_defaults(_handler=_handle_configure)

    serve = subparsers.add_parser("serve", help="Start the MCP server")
    serve.add_argument("--stdio", action="store_true", help="Use stdio transport")
    serve.set_defaults(_handler=_handle_serve)

    storage = subparsers.add_parser("storage", help="Manage artifact storage and quotas")
    storage_subparsers = storage.add_subparsers(dest="storage_command", required=True)

    storage_status = storage_subparsers.add_parser(
        "status", help="Show storage usage and quota status"
    )
    storage_status.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    storage_status.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed breakdown"
    )
    storage_status.set_defaults(_handler=_handle_storage_status)

    storage_prune = storage_subparsers.add_parser(
        "prune", help="Cleanup expired sessions and orphan files"
    )
    storage_prune.add_argument(
        "--older-than", "--days", type=int, dest="days", help="Override retention days"
    )
    storage_prune.add_argument(
        "--dry-run", "-n", action="store_true", help="Show what would be deleted"
    )
    storage_prune.add_argument(
        "--force", "-f", action="store_true", help="Execute deletion without confirmation"
    )
    storage_prune.add_argument(
        "--include-orphans", action="store_true", default=True, help="Also delete orphaned files"
    )
    storage_prune.add_argument(
        "--no-orphans", action="store_false", dest="include_orphans", help="Skip orphaned files"
    )
    storage_prune.set_defaults(_handler=_handle_storage_prune)

    storage_pin = storage_subparsers.add_parser(
        "pin", help="Pin or unpin a session to prevent auto-cleanup"
    )
    storage_pin.add_argument("session_id", help="Session ID to pin")
    storage_pin.add_argument(
        "--unpin", action="store_true", help="Unpin the session instead of pinning"
    )
    storage_pin.set_defaults(_handler=_handle_storage_pin)

    storage_list = storage_subparsers.add_parser(
        "list", help="List sessions and their storage impact"
    )
    storage_list.add_argument(
        "--state", choices=["active", "completed", "expired", "pinned"], help="Filter by state"
    )
    storage_list.add_argument("--limit", type=int, default=20, help="Max sessions to list")
    storage_list.add_argument(
        "--sort", choices=["age", "size", "name"], default="age", help="Sort criteria"
    )
    storage_list.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    storage_list.set_defaults(_handler=_handle_storage_list)

    return parser


def _print_error(code: str, message: str, *, details: object | None, debug: bool) -> None:
    print(f"ERROR[{code}]: {message}", file=sys.stderr)
    if details is not None and debug:
        print(json.dumps(details, indent=2, default=str), file=sys.stderr)


def _handle_install(args: argparse.Namespace) -> int:
    from bioimage_mcp.bootstrap.install import install

    return install(profile=args.profile)


def _handle_doctor(args: argparse.Namespace) -> int:
    from bioimage_mcp.bootstrap.doctor import doctor

    return doctor(json_output=args.json)


def _handle_configure(args: argparse.Namespace) -> int:
    from bioimage_mcp.bootstrap.configure import configure

    return configure()


def _handle_serve(args: argparse.Namespace) -> int:
    from bioimage_mcp.bootstrap.serve import serve

    return serve(stdio=args.stdio)


def _handle_storage_status(args: argparse.Namespace) -> int:
    from bioimage_mcp.config.loader import load_config
    from bioimage_mcp.storage.service import StorageService
    from bioimage_mcp.storage.sqlite import connect

    config = load_config()
    conn = connect(config)
    try:
        service = StorageService(config, conn)
        status = service.get_status()

        if args.json:
            print(status.model_dump_json(indent=2))
        else:
            print("=== Storage Usage ===")
            print(f"Total Capacity: {status.total_bytes / (1024**3):.2f} GB")
            print(
                f"Used:           {status.used_bytes / (1024**3):.2f} GB ({status.usage_percent:.1f}%)"
            )
            print(f"Orphan Files:   {status.orphan_bytes / (1024**2):.2f} MB")
            print("\nBy State:")
            for state, info in status.by_state.items():
                print(
                    f"  {state:10}: {info.session_count} sessions, {info.artifact_count} artifacts, {info.total_bytes / (1024**2):.2f} MB"
                )

        # Exit codes: 0=normal, 1=warning threshold, 2=critical threshold
        if status.usage_percent >= config.storage.critical_threshold * 100:
            return 2
        if status.usage_percent >= config.storage.warning_threshold * 100:
            return 1
        return 0
    finally:
        conn.close()


def _handle_storage_prune(args: argparse.Namespace) -> int:
    from bioimage_mcp.config.loader import load_config
    from bioimage_mcp.storage.service import StorageService
    from bioimage_mcp.storage.sqlite import connect

    config = load_config()
    conn = connect(config)
    try:
        service = StorageService(config, conn)

        result = service.prune(
            dry_run=args.dry_run, include_orphans=args.include_orphans, older_than_days=args.days
        )

        if args.dry_run:
            print("=== Prune Result (DRY RUN) ===")
        else:
            print("=== Prune Result ===")

        print(f"Sessions Deleted:     {result.sessions_deleted}")
        print(f"Artifacts Deleted:    {result.artifacts_deleted}")
        print(f"Bytes Reclaimed:      {result.bytes_reclaimed / (1024**2):.2f} MB")
        print(f"Orphan Files Deleted: {result.orphan_files_deleted}")

        if result.errors:
            print("\nErrors:")
            for err in result.errors:
                print(f"  - {err}")
            return 1  # Partial failure

        return 0
    finally:
        conn.close()


def _handle_storage_pin(args: argparse.Namespace) -> int:
    from bioimage_mcp.config.loader import load_config
    from bioimage_mcp.storage.service import StorageService
    from bioimage_mcp.storage.sqlite import connect

    config = load_config()
    conn = connect(config)
    try:
        service = StorageService(config, conn)
        try:
            if args.unpin:
                session = service.unpin_session(args.session_id)
                print(f"✓ Session {session.session_id} is now unpinned (available for cleanup)")
            else:
                session = service.pin_session(args.session_id)
                print(f"✓ Session {session.session_id} is now pinned (protected from cleanup)")

            # Show impact
            artifact_count = service.conn.execute(
                "SELECT COUNT(*) FROM artifacts WHERE session_id = ?", (session.session_id,)
            ).fetchone()[0]
            total_bytes = service.get_session_size(session.session_id)
            print(f"  - {artifact_count} artifacts, {total_bytes / (1024**3):.1f} GB total")

            return 0
        except KeyError:
            print(f"ERROR: Session {args.session_id} not found", file=sys.stderr)
            return 1
    finally:
        conn.close()


def _handle_storage_list(args: argparse.Namespace) -> int:
    from bioimage_mcp.config.loader import load_config
    from bioimage_mcp.storage.service import StorageService
    from bioimage_mcp.storage.sqlite import connect

    config = load_config()
    conn = connect(config)

    def format_size(bytes_val: int) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_val < 1024:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f} PB"

    def format_age(seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h {minutes % 60}m"
        days = hours // 24
        if days < 7:
            return f"{days}d {hours % 24}h"
        return f"{days}d"

    try:
        service = StorageService(config, conn)
        # Fetch all matching to get total count for the header
        all_summaries = service.list_sessions(state=args.state, limit=None, sort_by=args.sort)
        total_matching = len(all_summaries)
        summaries = all_summaries[: args.limit]

        if args.json:
            print(json.dumps([s.model_dump(mode="json") for s in summaries], indent=2))
        else:
            print(f"Sessions (showing {len(summaries)} of {total_matching})")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"{'SESSION ID':20} {'STATE':10} {'SIZE':10} {'AGE':10} {'ARTIFACTS'}")

            for s in summaries:
                pin = " [📌]" if s.is_pinned else ""
                sid_display = f"{s.session_id}{pin}"
                size_str = format_size(s.total_bytes)
                age_str = format_age(s.age_seconds)
                print(
                    f"{sid_display:20} {s.status:10} {size_str:10} {age_str:10} {s.artifact_count}"
                )

        return 0
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    handler = getattr(args, "_handler", None)
    if handler is None:
        parser.error("No command provided")

    try:
        return int(handler(args))
    except BioimageMcpError as exc:
        _print_error(exc.code, str(exc), details=exc.details, debug=bool(args.debug))
        return 1
    except PermissionError as exc:
        _print_error("PERMISSION", str(exc), details=None, debug=bool(args.debug))
        return 1
    except Exception as exc:  # noqa: BLE001
        if args.debug:
            raise
        _print_error("INTERNAL", f"{type(exc).__name__}: {exc}", details=None, debug=False)
        print("Re-run with --debug for traceback", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
