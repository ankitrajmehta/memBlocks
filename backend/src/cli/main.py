"""Interactive CLI for memBlocks — replaces the old root main.py."""

import asyncio
from typing import Any, Dict, Optional

from memblocks import MemBlocksClient, MemBlocksConfig


async def _run_cli() -> None:
    """Main async CLI loop."""
    config = MemBlocksConfig()
    client = MemBlocksClient(config)

    print("=" * 60)
    print("  memBlocks CLI")
    print("=" * 60)

    # ---- user setup ----
    user_id = input("\nEnter user ID (or press Enter for 'default_user'): ").strip()
    if not user_id:
        user_id = "default_user"

    user = await client.users.get_or_create_user(user_id)
    print(f"User: {user.get('user_id')}")

    # ---- block selection ----
    blocks = await client.blocks.get_user_blocks(user_id)

    block = None
    if blocks:
        print(f"\nFound {len(blocks)} existing block(s):")
        for i, b in enumerate(blocks, 1):
            print(f"  {i}. {b.name} ({b.meta_data.id})")

        choice = input("\nSelect block number, or press Enter to create new: ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(blocks):
                block = blocks[idx]

    if not block:
        name = input("New block name (Enter for 'My Memory'): ").strip() or "My Memory"
        desc = input("Block description (Enter to skip): ").strip()
        print("Creating block...")
        block = await client.blocks.create_block(
            user_id=user_id, name=name, description=desc
        )

    print(f"\nUsing block: {block.name} ({block.meta_data.id})")

    # ---- session setup ----
    engine = client.get_chat_engine(block)
    session_data: Dict[str, Any] = await engine.sessions.create_session(
        user_id=user_id,
        block_id=block.meta_data.id,
    )
    session_id: str = session_data["session_id"]
    print(f"Session: {session_id}")

    # ---- chat loop ----
    print("\nType your message (Ctrl+C or 'quit' to exit):\n")
    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break

            try:
                result = await engine.chat.send_message(
                    session_id=session_id,
                    user_message=user_input,
                )
                print(f"\nAssistant: {result['response']}\n")
            except Exception as e:
                print(f"Error: {e}\n")

    except KeyboardInterrupt:
        pass

    finally:
        print("\nClosing connections...")
        await client.close()
        print("Goodbye!")


def main() -> None:
    """Entry point for the `memblocks` CLI command."""
    asyncio.run(_run_cli())


if __name__ == "__main__":
    main()
