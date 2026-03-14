"""CLI for MemBlocks - set and get active memory block.

Provides `memblocks set-block <block_id>` and `memblocks get-block` commands.
"""

import argparse
import sys

from mcp_server.state import get_active_block_id, set_active_block_id


def cmd_set_block(args: argparse.Namespace) -> None:
    """Handle set-block command."""
    set_active_block_id(args.block_id)
    print(f"Active block set to: {args.block_id}")
    sys.exit(0)


def cmd_get_block(args: argparse.Namespace) -> None:
    """Handle get-block command."""
    block_id = get_active_block_id()
    if block_id:
        print(f"Active block: {block_id}")
    else:
        print("No active block set.")
    sys.exit(0)


def main() -> None:
    """Main entry point for the memblocks CLI."""
    parser = argparse.ArgumentParser(
        prog="memblocks",
        description="MemBlocks CLI - Manage active memory blocks",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # set-block subcommand
    p_set = subparsers.add_parser(
        "set-block",
        help="Set the active memory block",
    )
    p_set.add_argument(
        "block_id",
        help="Block ID to activate",
    )
    p_set.set_defaults(func=cmd_set_block)

    # get-block subcommand
    p_get = subparsers.add_parser(
        "get-block",
        help="Show the current active block",
    )
    p_get.set_defaults(func=cmd_get_block)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
