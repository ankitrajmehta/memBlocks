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

    user = await client.get_or_create_user(user_id)
    print(f"User: {user.get('user_id')}")

    # ---- block selection ----
    blocks = await client.get_user_blocks(user_id)

    block = None
    if blocks:
        print(f"\nFound {len(blocks)} existing block(s):")
        for i, b in enumerate(blocks, 1):
            print(f"  {i}. {b.name} ({b.id})")

        choice = input("\nSelect block number, or press Enter to create new: ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(blocks):
                block = blocks[idx]

    if not block:
        name = input("New block name (Enter for 'My Memory'): ").strip() or "My Memory"
        desc = input("Block description (Enter to skip): ").strip()
        print("Creating block...")
        block = await client.create_block(user_id=user_id, name=name, description=desc)

    print(f"\nUsing block: {block.name} ({block.id})")

    # ---- session setup ----
    session = await client.create_session(user_id=user_id, block_id=block.id)
    print(f"Session: {session.id}")

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
                # Retrieve memory context
                context = await block.retrieve(user_input)
                memory_window = await session.get_memory_window()
                summary = await session.get_recursive_summary()

                # Build system prompt
                system_parts = [
                    "You are a helpful assistant with memory of past conversations."
                ]
                if summary:
                    system_parts.append(
                        f"<Conversation Summary>\n{summary}\n</Conversation Summary>"
                    )
                memory_str = context.to_prompt_string()
                if memory_str:
                    system_parts.append(memory_str)
                system_prompt = "\n\n".join(system_parts)

                # Call LLM
                messages_for_llm = (
                    [{"role": "system", "content": system_prompt}]
                    + memory_window
                    + [{"role": "user", "content": user_input}]
                )
                ai_response = await client.llm.chat(messages=messages_for_llm)

                print(f"\nAssistant: {ai_response}\n")

                # Persist turn
                await session.add(user_msg=user_input, ai_response=ai_response)

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
