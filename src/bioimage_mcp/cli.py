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
    storage_status.set_defaults(_handler=_handle_storage_status)

    storage_prune = storage_subparsers.add_parser(
        "prune", help="Cleanup expired sessions and orphan files"
    )
    storage_prune.add_argument("--days", type=int, help="Override retention days")
    storage_prune.add_argument(
        "--force", action="store_true", help="Execute deletion without confirmation"
    )
    storage_prune.set_defaults(_handler=_handle_storage_prune)

    storage_pin = storage_subparsers.add_parser("pin", help="Pin a session to prevent auto-cleanup")
    storage_pin.add_argument("session_id", help="Session ID to pin")
    storage_pin.set_defaults(_handler=_handle_storage_pin)

    storage_unpin = storage_subparsers.add_parser("unpin", help="Unpin a session")
    storage_unpin.add_argument("session_id", help="Session ID to unpin")
    storage_unpin.set_defaults(_handler=_handle_storage_unpin)

    storage_list = storage_subparsers.add_parser(
        "list", help="List sessions and their storage impact"
    )
    storage_list.add_argument("--limit", type=int, default=20, help="Max sessions to list")
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
    print("Storage status: Not implemented")
    return 0


def _handle_storage_prune(args: argparse.Namespace) -> int:
    print(f"Storage prune (days={args.days}, force={args.force}): Not implemented")
    return 0


def _handle_storage_pin(args: argparse.Namespace) -> int:
    print(f"Storage pin (session_id={args.session_id}): Not implemented")
    return 0


def _handle_storage_unpin(args: argparse.Namespace) -> int:
    print(f"Storage unpin (session_id={args.session_id}): Not implemented")
    return 0


def _handle_storage_list(args: argparse.Namespace) -> int:
    print(f"Storage list (limit={args.limit}): Not implemented")
    return 0


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
