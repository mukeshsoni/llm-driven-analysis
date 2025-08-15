import asyncio
from llm_processor import LLMQueryProcessor


async def main():
    """Run the terminal chat application."""
    print("=" * 60)
    print("LLM Query Processor - Terminal Chat Mode")
    print("=" * 60)
    print("\nInitializing LLM processor...")

    # Use the context manager to ensure proper initialization and cleanup
    async with LLMQueryProcessor() as processor:
        print("Ready! Type 'exit', 'quit', or 'bye' to end the conversation.\n")
        print("-" * 60)
        await processor.chat_loop()

    print("\nChat session ended. Resources cleaned up.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
    except Exception as e:
        print(f"\nError: {e}")
