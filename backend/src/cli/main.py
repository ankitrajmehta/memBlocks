"""Interactive CLI for memBlocks — replaces the old root main.py."""

import asyncio
import json
import logging
from pathlib import Path

from memblocks import MemBlocksClient, MemBlocksConfig

LOG_DIR = Path("memblocks_cli_output")
LOG_DIR.mkdir(exist_ok=True)


class FlushingFileHandler(logging.FileHandler):
    """FileHandler that flushes to disk after every emitted record."""

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


def setup_logging() -> None:
    """Configure logging for the CLI and memblocks library."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[
            FlushingFileHandler(LOG_DIR / "cli.log"),
        ],
    )
    logging.getLogger("memblocks").setLevel(logging.DEBUG)
    logging.getLogger("memblocks").addHandler(
        FlushingFileHandler(LOG_DIR / "memblocks.log")
    )
    # Suppress noisy third-party loggers from the CLI
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("groq").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openinference").setLevel(logging.WARNING)


async def save_transparency_data(client: MemBlocksClient) -> None:
    """Overwrite transparency files with the latest data (fixed filenames for real-time updates)."""
    logger = logging.getLogger(__name__)

    # operation_log = client.get_operation_log()
    # if operation_log:
    #     ops = operation_log.get_entries(limit=1000)
    #     ops_data = [op.model_dump(mode="json") for op in ops]
    #     ops_file = LOG_DIR / "operation_log.json"
    #     with open(ops_file, "w") as f:
    #         json.dump(ops_data, f, indent=2)
    #     # logger.debug(f"Updated {ops_file}")

    #     summary = operation_log.summary()
    #     summary_file = LOG_DIR / "operation_summary.json"
    #     with open(summary_file, "w") as f:
    #         json.dump(summary, f, indent=2, default=str)
    #     # logger.debug(f"Updated {summary_file}")

    retrieval_log = client.get_retrieval_log()
    if retrieval_log:
        retrievals = retrieval_log.get_entries(limit=1000)
        retrieval_data = [r.model_dump(mode="json") for r in retrievals]
        retrieval_file = LOG_DIR / "retrieval_log.json"
        with open(retrieval_file, "w") as f:
            json.dump(retrieval_data, f, indent=2)
        # logger.debug(f"Updated {retrieval_file}")

    processing_history = client.get_processing_history()
    if processing_history:
        runs = processing_history.get_runs(limit=100)
        runs_data = [run.model_dump(mode="json") for run in runs]
        history_file = LOG_DIR / "processing_history.json"
        with open(history_file, "w") as f:
            json.dump(runs_data, f, indent=2)
        # logger.debug(f"Updated {history_file}")


async def ainput(prompt: str = "") -> str:
    """Non-blocking input using asyncio.to_thread (requires Python 3.9+)."""
    return await asyncio.to_thread(input, prompt)


async def _run_cli() -> None:
    """Main async CLI loop."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting memBlocks CLI")

    config = MemBlocksConfig()  # reads from environment variables or a .env file
    client = MemBlocksClient(config)

    def on_event(event_name: str, payload: dict) -> None:
        logger.info(f"Event: {event_name} - {json.dumps(payload, default=str)}")
        # Refresh transparency files after each pipeline completes or fails
        if event_name in (
            "on_pipeline_completed",
            "on_pipeline_failed",
            "on_memory_stored",
            "on_memory_retrieved",
        ):
            asyncio.create_task(save_transparency_data(client))

    events = [
        "on_memory_extracted",
        "on_conflict_resolved",
        "on_memory_stored",
        "on_core_memory_updated",
        "on_summary_generated",
        "on_pipeline_started",
        "on_pipeline_completed",
        "on_pipeline_failed",
        "on_memory_retrieved",
        "on_db_write",
        "on_message_processed",
    ]
    for event in events:
        client.subscribe(event, lambda p, e=event: on_event(e, p))

    print("=" * 60)
    print("  memBlocks CLI")
    print("=" * 60)

    # ---- user setup ----
    user_id = (
        await ainput("\nEnter user ID (or press Enter for 'default_user'): ")
    ).strip()
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

        choice = (
            await ainput("\nSelect block number, or press Enter to create new: ")
        ).strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(blocks):
                block = blocks[idx]

    if not block:
        name = (
            await ainput("New block name (Enter for 'My Memory'): ")
        ).strip() or "My Memory"
        desc = (await ainput("Block description (Enter to skip): ")).strip()
        print("Creating block...")
        block = await client.create_block(user_id=user_id, name=name, description=desc)

    print(f"\nUsing block: {block.name} ({block.id})")

    # ---- session setup ----
    session = await client.create_session(user_id=user_id, block_id=block.id)
    print(f"Session: {session.id}")

    # ---- chat loop ----
    # helper: persist turns in background to avoid blocking the chat loop
    async def _persist_turn(session, user_msg, ai_response) -> None:
        try:
            await session.add(user_msg=user_msg, ai_response=ai_response)
        except Exception as e:
            print(f"Warning: failed to persist turn: {e}")

    print("\nType your message (Ctrl+C or 'quit' to exit):\n")
    try:
        while True:
            try:
                user_input = (await ainput("You: ")).strip()
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

                # Persist turn in background (don't await so loop stays responsive)
                asyncio.create_task(_persist_turn(session, user_input, ai_response))

            except Exception as e:
                print(f"Error: {e}\n")

    except KeyboardInterrupt:
        pass

    finally:
        print("\nFlushing final transparency data...")
        await save_transparency_data(client)
        print("\nClosing connections...")
        await client.close()
        print("Goodbye!")


def main() -> None:
    """Entry point for the `memblocks` CLI command."""
    asyncio.run(_run_cli())


if __name__ == "__main__":
    main()
