import argparse
import pytest
from bioimage_mcp.cli import _build_parser


def test_cli_storage_subparser():
    parser = _build_parser()

    # Test 'storage' command existence
    # We use parse_args([]) to trigger error if no command,
    # but we want to check if 'storage' is in the choices
    subparsers_action = next(
        a for a in parser._actions if isinstance(a, argparse._SubParsersAction)
    )
    assert "storage" in subparsers_action.choices

    storage_parser = subparsers_action.choices["storage"]
    storage_subparsers = next(
        a for a in storage_parser._actions if isinstance(a, argparse._SubParsersAction)
    )

    assert "status" in storage_subparsers.choices
    assert "prune" in storage_subparsers.choices
    assert "pin" in storage_subparsers.choices
    assert "unpin" in storage_subparsers.choices
    assert "list" in storage_subparsers.choices


def test_cli_storage_pin_args():
    parser = _build_parser()
    args = parser.parse_args(["storage", "pin", "sess_123"])
    assert args.command == "storage"
    assert args.storage_command == "pin"
    assert args.session_id == "sess_123"


def test_cli_storage_unpin_args():
    parser = _build_parser()
    args = parser.parse_args(["storage", "unpin", "sess_123"])
    assert args.command == "storage"
    assert args.storage_command == "unpin"
    assert args.session_id == "sess_123"


def test_cli_storage_prune_args():
    parser = _build_parser()
    args = parser.parse_args(["storage", "prune", "--days", "5", "--force"])
    assert args.command == "storage"
    assert args.storage_command == "prune"
    assert args.days == 5
    assert args.force is True


def test_cli_storage_list_args():
    parser = _build_parser()
    args = parser.parse_args(["storage", "list"])
    assert args.command == "storage"
    assert args.storage_command == "list"
    assert args.limit == 50
    assert args.sort == "age"
